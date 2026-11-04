"""Voxel volume -> planar panels + straight strips.

Every candidate panel is (plane, connected region of that plane's section through the
volume). Panels are chosen greedily by how much not-yet-covered volume they explain,
and each new panel must cross the structure built so far. Runs on the CPU.
"""
from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi


def plane_basis(n):
    n = n / np.linalg.norm(n)
    a = np.array([0.0, 0, 1]) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(a, n)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u)  # for vertical planes: u horizontal, v = up


def directions(n_sphere=400, n_vertical=72):
    """Plane normals: Fibonacci hemisphere + an explicit family of vertical planes + horizontal."""
    i = np.arange(n_sphere) + 0.5
    phi = np.arccos(1 - i / n_sphere)
    th = np.pi * (1 + 5 ** 0.5) * i
    a = np.linspace(0, np.pi, n_vertical, endpoint=False)
    return np.concatenate([
        np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1),
        np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], 1),
        np.array([[0, 0, 1.0]]),
    ]).astype(np.float32)


@dataclass
class Volume:
    occ: np.ndarray        # bool [X,Y,Z]
    h: float
    origin: np.ndarray     # coords of voxel (0,0,0) corner

    def lookup(self, X):
        idx = np.floor((X - self.origin) / self.h).astype(np.int64)
        ok = np.all((idx >= 0) & (idx < self.occ.shape), axis=-1)
        out = np.zeros(X.shape[:-1], bool)
        i = idx[ok]
        out[ok] = self.occ[i[:, 0], i[:, 1], i[:, 2]]
        return out

    def points(self, stride=1):
        o = self.occ[::stride, ::stride, ::stride] if stride > 1 else self.occ
        return self.origin + (np.argwhere(o) * stride + 0.5 * stride) * self.h


@dataclass
class Element:
    n: np.ndarray
    c: float
    u: np.ndarray
    v: np.ndarray
    uv0: np.ndarray        # (u,v) of raster pixel (0,0) corner
    px: float
    mask: np.ndarray       # bool [W,H] region in plane raster (u along axis 0)
    gain: float = 0.0
    order: int = 0

    def pix_to_world(self, ij):
        uv = self.uv0 + (np.asarray(ij, float) + 0.5) * self.px
        return self.c * self.n + uv[..., :1] * self.u + uv[..., 1:2] * self.v

    def world_to_pix(self, X):
        uv = np.stack([X @ self.u, X @ self.v], -1)
        return np.floor((uv - self.uv0) / self.px).astype(np.int64)

    def contains(self, X, dilate_px=0):
        m = ndi.binary_dilation(self.mask, iterations=dilate_px) if dilate_px else self.mask
        ij = self.world_to_pix(X)
        ok = np.all((ij >= 0) & (ij < m.shape), -1)
        out = np.zeros(len(X), bool)
        out[ok] = m[ij[ok, 0], ij[ok, 1]]
        return out

    def world_pixels(self):
        return self.pix_to_world(np.argwhere(self.mask))

    def area(self):
        return float(self.mask.sum() * self.px ** 2)


def section(vol, n, c, uv_lo, uv_hi, px):
    u, v = plane_basis(n)
    W, H = np.ceil((uv_hi - uv_lo) / px).astype(int)
    gu = uv_lo[0] + (np.arange(W) + 0.5) * px
    gv = uv_lo[1] + (np.arange(H) + 0.5) * px
    X = c * n + gu[:, None, None] * u + gv[None, :, None] * v
    return vol.lookup(X.reshape(-1, 3)).reshape(W, H), u, v


def slab_scores(bins, wu, nb, k):
    """Weighted count of uncovered points within +-k bins, per (direction, offset)."""
    D = len(bins)
    hist = np.empty((D, nb))
    for d in range(D):
        hist[d] = np.bincount(bins[d], weights=wu, minlength=nb)
    slab = ndi.uniform_filter1d(hist, 2 * k + 1, axis=1, mode="constant") * (2 * k + 1)
    peak = ndi.maximum_filter1d(slab, 2 * k + 1, axis=1, mode="constant")
    return np.where(slab >= peak - 1e-9, slab, 0).ravel()


def select_panels(vol, delta=0.2, max_panels=20, target_coverage=0.85, min_area=0.04, px=0.025,
                  top_m=400, parallel_deg=15, parallel_dist=1.5, boundary_weight=3.0, max_tilt_deg=35,
                  min_cross_deg=45, max_points=80_000, seed=0, log=print):
    rng = np.random.default_rng(seed)
    P = vol.points(2)
    if not len(P):
        P = vol.points(1)
    if len(P) > max_points:
        P = P[rng.choice(len(P), max_points, replace=False)]
    # voxels near the surface weigh more, so silhouettes get represented
    shell = Volume(vol.occ & ~ndi.binary_erosion(vol.occ, iterations=3), vol.h, vol.origin)
    w = np.where(shell.lookup(P), boundary_weight, 1.0)
    total = w.sum()

    Dn = directions()
    Dn = Dn[np.abs(Dn[:, 2]) <= np.sin(np.radians(max_tilt_deg)) + 1e-6]   # steep planes only
    S = Dn @ P.T.astype(np.float32)
    bw = 0.02
    smin = float(S.min()) - 0.1
    nb = int((float(S.max()) - smin) / bw) + 2
    bins = ((S - smin) / bw).astype(np.int32)
    del S
    k = int(round(delta / bw))

    covered = np.zeros(len(P), bool)
    chosen = []
    dead = set()   # (direction, bin) with no usable section at all
    for it in range(max_panels):
        score = slab_scores(bins, np.where(covered, 0.0, w), nb, k)
        top = np.flatnonzero(score)
        top = top[np.argsort(-score[top])]
        best, tried = None, 0
        for t in top:
            sc = score[t]
            if sc <= 0 or (best and sc <= best[0]):
                break  # slab gain upper-bounds region gain
            di, bi = divmod(int(t), nb)
            if (di, bi) in dead:
                continue
            tried += 1
            if tried > top_m:
                break
            n = Dn[di].astype(np.float64)
            n /= np.linalg.norm(n)
            c = smin + (bi + 0.5) * bw
            u, v = plane_basis(n)
            Q = np.stack([P @ u, P @ v], 1)
            uv0 = Q.min(0) - 0.1
            sec, u, v = section(vol, n, c, uv0, Q.max(0) + 0.1, px)
            lab, nl = ndi.label(sec)
            areas = np.bincount(lab.ravel(), minlength=nl + 1) * px * px
            areas[0] = 0
            if nl == 0 or areas.max() < min_area:
                dead.add((di, bi))
                continue
            in_slab = np.flatnonzero(np.abs(P @ n - c) < delta)
            ij = np.floor((Q[in_slab] - uv0) / px).astype(int)
            okp = np.all((ij >= 0) & (ij < sec.shape), 1)
            lab_d = ndi.grey_dilation(lab, size=3)
            plab = np.zeros(len(in_slab), int)
            plab[okp] = lab_d[ij[okp, 0], ij[okp, 1]]
            wl = np.bincount(plab, weights=np.where(covered[in_slab], 0, w[in_slab]), minlength=nl + 1)
            wl[0] = 0
            for l in np.argsort(-wl):
                if l == 0 or wl[l] <= 0 or (best and wl[l] <= best[0]):
                    break
                if areas[l] < min_area:
                    continue
                e = Element(n, c, u, v, uv0, px, lab == l)
                if chosen and not _crosses_well(e, chosen, vol.h, min_cross_deg):
                    continue
                if _too_parallel(e, chosen, parallel_deg, parallel_dist * delta):
                    continue
                best = (wl[l], e, in_slab[plab == l])
                break
        if best is None:
            log(f"  第 {it + 1} 片之後沒有可用的板了 / これ以上の板は見つからない")
            break
        g, e, cov_idx = best
        e.gain, e.order = float(g / total), len(chosen)
        covered[cov_idx] = True
        chosen.append(e)
        cov = (w * covered).sum() / total
        log(f"  板 P{len(chosen):02d}  面積 {e.area():5.2f}  涵蓋率 {cov:.0%}")
        if cov >= target_coverage:
            break
    return chosen


def _contacts(e, chosen, h):
    """Other panels this one actually crosses, with the sine of the crossing angle."""
    X = e.world_pixels()
    out = []
    for o in chosen:
        near = np.abs(X @ o.n - o.c) < 0.75 * h
        if near.any() and o.contains(X[near], dilate_px=1).sum() >= 3:
            out.append((o, float(np.linalg.norm(np.cross(e.n, o.n)))))
    return out


def _crosses_well(e, chosen, h, min_cross_deg):
    """Must touch the structure, and every crossing must be steep enough to make a joint."""
    hits = _contacts(e, chosen, h)
    return bool(hits) and all(s >= np.sin(np.radians(min_cross_deg)) for _, s in hits)


def _too_parallel(e, chosen, deg, dist):
    X = e.world_pixels()
    for o in chosen:
        if abs(e.n @ o.n) > np.cos(np.radians(deg)):
            d = X @ o.n - o.c
            close = np.abs(d) < dist
            if close.sum() and o.contains(X[close] - np.outer(d[close], o.n), 2).mean() > 0.2:
                return True
    return False


def select_strips(vol, panels, n_strips=6, min_len=1.0, max_len=4.0, min_inside=0.85, min_pierce=2,
                  overhang=0.12, n_cand=6000, min_angle_deg=20, min_pierce_deg=35, clearance=0.15,
                  seed=0, log=print):
    """Long straight sticks through the volume. A candidate between two interior points must stay
    mostly inside, pass through several panels, and meet each of them steeply enough to drill."""
    if n_strips <= 0 or not panels:
        return []
    rng = np.random.default_rng(seed)
    Pin = Volume(ndi.binary_erosion(vol.occ, iterations=2), vol.h, vol.origin).points(2)
    if not len(Pin):
        return []
    A = Pin[rng.integers(len(Pin), size=n_cand)]
    B = Pin[rng.integers(len(Pin), size=n_cand)]
    L = np.linalg.norm(B - A, axis=1)
    keep = (L > min_len) & (L < max_len)
    A, B, L = A[keep], B[keep], L[keep]
    if not len(A):
        return []
    pts = A[:, None] + (B - A)[:, None] * np.linspace(0, 1, 64)[None, :, None]
    ok = vol.lookup(pts.reshape(-1, 3)).reshape(len(A), -1).mean(1) >= min_inside
    A, B, L = A[ok], B[ok], L[ok]
    D = (B - A) / L[:, None]
    pierce = np.zeros((len(A), len(panels)), bool)
    shallow = np.zeros(len(A), bool)
    for k, e in enumerate(panels):
        da, db = A @ e.n - e.c, B @ e.n - e.c
        cross = (da * db) < 0
        if not cross.any():
            continue
        t = da[cross] / (da[cross] - db[cross])
        hit = e.contains(A[cross] + (B - A)[cross] * t[:, None], dilate_px=1)
        ci = np.flatnonzero(cross)
        pierce[ci, k] = hit
        shallow[ci[hit]] |= np.abs(D[ci[hit]] @ e.n) < np.sin(np.radians(min_pierce_deg))
    npi = pierce.sum(1)
    ok = (npi >= min_pierce) & ~shallow
    A, B, L, D, npi, pierce = A[ok], B[ok], L[ok], D[ok], npi[ok], pierce[ok]
    score = npi * L
    out = []
    ts = np.linspace(0, 1, 16)
    for _ in range(n_strips):
        if not len(score) or score.max() <= 0:
            break
        i = int(score.argmax())
        a, b, d = A[i], B[i], D[i]
        out.append({"a": a - d * overhang, "b": b + d * overhang, "length": float(L[i] + 2 * overhang),
                    "pierces": np.flatnonzero(pierce[i]).tolist()})
        # spread out: no similar direction nearby, and never touching a strip already placed
        ang = np.degrees(np.arccos(np.clip(np.abs(D @ d), 0, 1)))
        mid = (A + B) / 2
        dist = np.linalg.norm(np.cross(mid - a, d), axis=1)
        score = np.where((ang < min_angle_deg) & (dist < 0.6), 0, score)
        S = A[:, None] + (B - A)[:, None] * ts[None, :, None]
        Q = a + (b - a) * ts[:, None]
        gap = np.linalg.norm(S[:, :, None] - Q[None, None], axis=-1).min((1, 2))
        score = np.where(gap < clearance, 0, score)
        score = np.where(np.linalg.norm(mid - (a + b) / 2, axis=1) < 0.5, score * 0.5, score)
        score[i] = 0
    log(f"  木條 {len(out)} 根 / 角材 {len(out)} 本")
    return out
