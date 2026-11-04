"""Panels -> parts you can actually cut and assemble. Everything here is in millimetres.

Cross-lap joints: where two panels cross, each gets a slot to the middle of the contact.
The slot directions come from one assembly order: every later panel drops onto the earlier
ones from above, so a valid order exists by construction. A slot always runs out to the
panel's outer edge, otherwise the other panel could not slide in.

3-axis CNC walls are square to the sheet, so a slot for panels crossing at angle a must be
widened to t (1 + cos a) / sin a, and a stick passing at an angle needs a hole that clears
the full board thickness.
"""
import itertools

import numpy as np
from shapely.affinity import translate
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import polylabel, unary_union
from skimage import measure
from scipy import ndimage as ndi


def mask_to_geom(mask, px, uv0, scale, simplify=0.002):
    """Binary raster (u along axis 0) -> shapely geometry in plane (u, v) millimetres."""
    m = ndi.gaussian_filter(np.pad(mask, 2).astype(float), 1.0)
    rings = []
    for c in measure.find_contours(m, 0.5):
        uv = uv0 + (c - 2 + 0.5) * px
        if len(uv) >= 4:
            p = Polygon(uv).buffer(0)
            if p.area > 4 * px * px:
                rings.append(p)
    if not rings:
        return None
    geom = rings[0]
    for r in rings[1:]:          # even-odd nesting: XOR gives the solid with its holes
        geom = geom.symmetric_difference(r)
    geom = geom.simplify(simplify, preserve_topology=True).buffer(0)
    return _scale(geom, scale)


def _scale(g, k):
    from shapely.affinity import scale
    return scale(g, k, k, origin=(0, 0))


def polys(g):
    if g is None or g.is_empty:
        return []
    return [p for p in (g.geoms if hasattr(g, "geoms") else [g]) if p.geom_type == "Polygon" and not p.is_empty]


def filled(g):
    return unary_union([Polygon(p.exterior) for p in polys(g)])


def tool_safe(g, tool, round_mm=8.0):
    """Round the voxel steps away. Inside corners end up at least the tool radius, gaps the
    tool cannot enter close up, and outside corners get a soft edge."""
    r = max(tool / 2 * 1.02, round_mm)
    g = g.buffer(r, quad_segs=12).buffer(-2 * r, quad_segs=12).buffer(r, quad_segs=12)
    return g.simplify(0.15)


def _intervals(g, a, b):
    """Parts of segment a->b inside g, in millimetres from a."""
    L = np.linalg.norm(b - a)
    hit = LineString([a, b]).intersection(g)
    out = []
    for s in getattr(hit, "geoms", [hit]):
        if s.is_empty or s.geom_type != "LineString":
            continue
        c = np.array(s.coords)
        t = sorted(np.dot(x - a, b - a) / L for x in (c[0], c[-1]))
        out.append((t[0], t[1]))
    return sorted(out)


def find_contacts(panels, k, t, min_len=5.0):
    """Where pairs of panels cross. Line direction always points up. Outlines are grown by half
    a slot first: two boards can collide even when their centre planes just miss, and the
    shallower the angle, the further from the crossing line they touch.
    Pairs that cross in plan but sit one above the other have no spans: nothing to cut, but
    the lower one must go in first or the upper one will hit it on the way down."""
    out = []
    solid = {p["id"]: filled(p["g"]) for p in panels}
    for A, B in itertools.combinations(panels, 2):
        d = np.cross(A["n"], B["n"])
        s = np.linalg.norm(d)
        if s < 0.1:
            continue
        d = d / s
        if d[2] < 0 or (d[2] == 0 and d[0] < 0):
            d = -d
        X0 = np.linalg.solve(np.stack([A["n"], B["n"], d]), [A["c"], B["c"], 0])
        span = 16.0
        pa, pb = X0 - span * d, X0 + span * d                     # design units
        uv = lambda p, X: np.array([X @ p["u"], X @ p["v"]]) * k
        angle = float(np.degrees(np.arcsin(min(s, 1.0))))
        grow = slot_width(t, angle, 0) / 2 + 1
        Ia = _intervals(solid[A["id"]].buffer(grow), uv(A, pa), uv(A, pb))
        Ib = _intervals(solid[B["id"]].buffer(grow), uv(B, pa), uv(B, pb))
        if not Ia or not Ib:
            continue
        spans = [(max(a0, b0), min(a1, b1)) for a0, a1 in Ia for b0, b1 in Ib if min(a1, b1) - max(a0, b0) >= min_len]
        out.append(dict(a=A["id"], b=B["id"], d=d, pa=pa, pb=pb, spans=spans, Ia=Ia, Ib=Ib, angle=angle))
    return out


BLOCKED = 1e6   # cost of an order that drops one panel through another


def order_cost(c, first):
    """Extra slot length (past the contact) if panel `first` goes in before the other one.
    The earlier panel's slot opens upward, the later one's downward."""
    I1, I2 = (c["Ia"], c["Ib"]) if first == c["a"] else (c["Ib"], c["Ia"])
    if not c["spans"]:
        return BLOCKED if min(b for b, _ in I1) > max(e for _, e in I2) else 0.0
    return sum(max(e for _, e in I1) - s1 + s0 - min(b for b, _ in I2) for s0, s1 in c["spans"])


def best_order(ids, contacts, seed=0, tries=400):
    """Assembly order with the least extra slot length (random restarts + swaps)."""
    pair = {}
    for c in contacts:
        pair[(c["a"], c["b"])] = order_cost(c, c["a"])
        pair[(c["b"], c["a"])] = order_cost(c, c["b"])
    cost = lambda o: sum(pair.get((o[i], o[j]), 0) for i in range(len(o)) for j in range(i + 1, len(o)))
    rng = np.random.default_rng(seed)
    best, best_c = list(ids), cost(list(ids))
    for _ in range(tries):
        o = list(rng.permutation(ids))
        c0 = cost(o)
        improved = True
        while improved:
            improved = False
            for i in range(len(o) - 1):
                o[i], o[i + 1] = o[i + 1], o[i]
                c1 = cost(o)
                if c1 < c0 - 1e-9:
                    c0, improved = c1, True
                else:
                    o[i], o[i + 1] = o[i + 1], o[i]
        if c0 < best_c - 1e-9:
            best, best_c = o, c0
    return [int(i) for i in best], best_c >= BLOCKED


def slot_width(t, angle_deg, tol):
    a = np.radians(angle_deg)
    return t * (1 + np.cos(a)) / np.sin(a) + tol


def slot_poly(p_close, p_open, w, tool, overrun=30.0):
    """Slot from a closed end to past the panel edge, with dogbones at the closed end."""
    d = (p_open - p_close) / np.linalg.norm(p_open - p_close)
    n = np.array([-d[1], d[0]]) * w / 2
    end = p_open + d * overrun
    g = Polygon([p_close + n, end + n, end - n, p_close - n])
    r = tool / 2 * 1.02
    if w > 2 * r:
        off = r / np.sqrt(2)
        for s in (1, -1):
            corner = p_close + s * n
            g = g.union(Point(*(corner + d * off - s * n / np.linalg.norm(n) * off)).buffer(r, quad_segs=12))
    return g


def cut_joints(panels, contacts, order, cfg):
    """Slots for every contact. Returns (slots per panel, joint records)."""
    t, tol, tool = cfg["thickness_mm"], cfg["tolerance_mm"], cfg["tool_diameter_mm"]
    rank = {pid: i for i, pid in enumerate(order)}
    by_id = {p["id"]: p for p in panels}
    k = cfg["_k"]
    slots = {p["id"]: [] for p in panels}
    joint_of = {p["id"]: [] for p in panels}
    joints = []
    for c in contacts:
        early, late = (c["a"], c["b"]) if rank[c["a"]] < rank[c["b"]] else (c["b"], c["a"])
        Ie, Il = (c["Ia"], c["Ib"]) if early == c["a"] else (c["Ib"], c["Ia"])
        w = slot_width(t, c["angle"], tol)
        at = lambda p, s: np.array([(c["pa"] + c["d"] * (s / k)) @ p["u"], (c["pa"] + c["d"] * (s / k)) @ p["v"]]) * k
        for s0, s1 in c["spans"]:
            m = (s0 + s1) / 2
            E, Lp = by_id[early], by_id[late]
            slots[early].append(slot_poly(at(E, m), at(E, max(e for _, e in Ie)), w, tool))
            slots[late].append(slot_poly(at(Lp, m), at(Lp, min(b for b, _ in Il)), w, tool))
            joint_of[early].append(len(joints))
            joint_of[late].append(len(joints))
            joints.append(dict(early=early, late=late, angle=round(c["angle"], 1), width=round(float(w), 2),
                               length=round(float(s1 - s0), 1), up=[round(float(x), 3) for x in c["d"]]))
    return slots, joint_of, joints


def joint_spread(joints):
    """Largest angle between two joints on the same panel. Above a few degrees it will not slide in."""
    by = {}
    for j in joints:
        for pid in (j["early"], j["late"]):
            by.setdefault(pid, []).append(np.array(j["up"]))
    worst = 0.0
    for ds in by.values():
        for x, y in itertools.combinations(ds, 2):
            worst = max(worst, float(np.degrees(np.arccos(np.clip(x @ y, -1, 1)))))
    return worst


def strip_frame(d):
    """Cross-section axes of a stick along d (same convention as the 3D viewer)."""
    z = np.array([0, 0, 1.0])
    ax = np.cross(z, d)
    s, c = np.linalg.norm(ax), z @ d
    if s < 1e-9:
        R = np.eye(3) if c > 0 else np.diag([1.0, -1, -1])
    else:
        ax /= s
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        R = np.eye(3) + s * K + (1 - c) * K @ K
    return R[:, 0], R[:, 1]


def _footprint(p, a, d, L, e1, e2, cfg, clip=True):
    """Hull of a stick where it passes through a panel's slab, in plane mm; None if it never does.
    With clip=False the stick is treated as infinitely long. Also returns where along it."""
    from shapely.geometry import MultiPoint
    t, k, tol = cfg["thickness_mm"], cfg["_k"], cfg["tolerance_mm"]
    sw, sh = (x + tol for x in cfg["strip_section_mm"])     # the hole clears the stick on every side
    dn = d @ p["n"]
    A = a * k                                                # stick start, mm
    if abs(dn) < 1e-6:                                       # running parallel to the panel
        if abs(A @ p["n"] - p["c"] * k) > t / 2 + max(sw, sh):
            return None, 0.0
        ends = [A, A + d * L]
        return LineString([(x @ p["u"], x @ p["v"]) for x in ends]).buffer(max(sw, sh) / 2), L / 2
    corners = [A + sx * sw * e1 + sy * sh * e2 for sx, sy in itertools.product((-.5, .5), repeat=2)]
    spans = [sorted(((p["c"] * k + f - q @ p["n"]) / dn) for f in (-t / 2, t / 2)) for q in corners]
    t0, t1 = (-2.0, L + 2) if clip else (-np.inf, np.inf)
    if clip and not any(lo <= t1 and hi >= t0 for lo, hi in spans):
        return None, 0.0
    pts, taus = [], []
    for q, (lo, hi) in zip(corners, spans):
        for tau in (min(max(lo, t0), t1), min(max(hi, t0), t1)):
            y = q + d * tau
            pts.append((y @ p["u"], y @ p["v"]))
            taus.append(tau)
    # a stick that ends inside the board: its whole end face counts, not just the corners
    for end in (t0, t1):
        if min(lo for lo, _ in spans) <= end <= max(hi for _, hi in spans):
            for q in corners:
                y = q + d * end
                pts.append((y @ p["u"], y @ p["v"]))
    hull = MultiPoint(pts).convex_hull          # a grazing stick may only give a point or a line
    return (hull if hull.geom_type == "Polygon" else hull.buffer(0.5)), float(np.mean(taus))


def strip_holes(panels, strips, cfg, want, min_pierce_deg=35, log=print):
    """Holes that clear each stick through the full board thickness. A stick is dropped if it
    grazes a panel, ends up in fewer than two, or has panels blocking both ways in."""
    tol, k = cfg["tolerance_mm"], cfg["_k"]
    outline = {p["id"]: filled(p["g"]) for p in panels}
    holes = {p["id"]: [] for p in panels}
    kept = []
    for s in strips:
        if len(kept) == want:
            break
        a, b = np.asarray(s["a"]), np.asarray(s["b"])
        L = np.linalg.norm(b - a) * k
        d = (b - a) / np.linalg.norm(b - a)
        e1, e2 = strip_frame(d)
        hits, blocked, bad = [], set(), False
        for p in panels:
            h, _ = _footprint(p, a, d, L, e1, e2, cfg)
            if h is not None and h.intersects(outline[p["id"]]):
                if abs(d @ p["n"]) < np.sin(np.radians(min_pierce_deg)):
                    bad = True
                    break
                hits.append((p["id"], h))
                continue
            h, tau = _footprint(p, a, d, L, e1, e2, cfg, clip=False)
            if h is not None and h.intersects(outline[p["id"]]):
                blocked.add(1 if tau > L / 2 else -1)
        if bad or len(hits) < 2 or len(blocked) == 2:
            continue
        for pid, h in hits:
            holes[pid].append(h.buffer(tol / 2 + 1e-3))
        kept.append(dict(s, pierces=[pid for pid, _ in hits]))
    return holes, kept


def make_parts(panels, slots, holes, joint_of, min_piece=3000.0):
    """Cut slots and holes out of each panel. A panel that falls apart becomes P03a, P03b...
    Scraps too small to matter are dropped. Each part remembers which joints it touches."""
    parts, scrap = [], 0
    for p in panels:
        pid = p["id"]
        cut = p["g"].difference(unary_union(slots[pid] + holes[pid])) if slots[pid] or holes[pid] else p["g"]
        pieces = sorted(polys(cut), key=lambda g: -g.area)
        keep = [g for g in pieces if g.area >= min_piece] or pieces[:1]
        scrap += len(pieces) - len(keep)
        for i, g in enumerate(keep):
            parts.append(dict(id=pid, name=f"P{pid:02d}" + ("abcdefgh"[i] if len(keep) > 1 else ""), geom=g,
                              holes=[h for h in holes[pid] if h.intersects(g.buffer(1))],
                              joints={j for s, j in zip(slots[pid], joint_of[pid]) if g.distance(s) < 1.0}))
    return parts, scrap


def loose_parts(parts):
    """Parts not joined to the biggest connected group."""
    group = list(range(len(parts)))
    find = lambda i: i if group[i] == i else find(group[i])
    for i, a in enumerate(parts):
        for j in range(i + 1, len(parts)):
            if a["joints"] & parts[j]["joints"]:
                group[find(i)] = find(j)
    roots = [find(i) for i in range(len(parts))]
    main = max(set(roots), key=lambda r: sum(parts[i]["geom"].area for i in range(len(parts)) if roots[i] == r))
    return [q["name"] for q, r in zip(parts, roots) if r != main]


def label_point(g):
    return polylabel(g, tolerance=2.0)


def nest(parts, sheet, margin, gap, step=20.0):
    """Bottom-left fill on the real outlines. Returns placements, or raises if a part is too big."""
    from shapely.affinity import rotate
    from shapely.prepared import prep
    W, H = sheet
    sheets = []                    # union of what is already on each sheet
    placed = []
    for q in sorted(parts, key=lambda x: -Polygon(x["geom"].exterior).area):
        shape = Polygon(q["geom"].exterior).simplify(1.5)
        best = None
        for si in range(len(sheets) + 1):
            used = sheets[si] if si < len(sheets) else None
            pu = prep(used.buffer(gap)) if used is not None else None
            for ang in range(0, 360, 30):
                g = rotate(shape, ang, origin=(0, 0))
                x0, y0, x1, y1 = g.bounds
                w, h = x1 - x0, y1 - y0
                if w > W - 2 * margin or h > H - 2 * margin:
                    continue
                found = None
                for yy in np.arange(margin, H - margin - h + 1e-6, step):
                    for xx in np.arange(margin, W - margin - w + 1e-6, step):
                        if pu is None or not pu.intersects(translate(g, xx - x0, yy - y0)):
                            found = (yy + h, xx, ang, xx - x0, yy - y0)
                            break
                    if found:
                        break
                if found and (best is None or found[:2] < best[1][:2]):
                    best = (si, found)
            if best is not None:
                break
        if best is None:
            x0, y0, x1, y1 = q["geom"].bounds
            raise ValueError(f"{q['name']} 放不進板材（{x1 - x0:.0f} × {y1 - y0:.0f} mm）："
                             "請把 size_mm 改小，或把 sheet_mm 改大 / 部品が板に入らない")
        si, (_, _, ang, dx, dy) = best
        tf = lambda G: translate(rotate(G, ang, origin=(0, 0)), dx, dy)
        if si == len(sheets):
            sheets.append(tf(shape))
        else:
            sheets[si] = unary_union([sheets[si], tf(shape)])
        placed.append(dict(q, sheet=si, placed=tf(q["geom"]), placed_holes=[tf(h) for h in q["holes"]]))
    return placed, len(sheets)


def stability(panels, k):
    """Is the centre of mass over the feet? Returns (ok, margin_mm or None)."""
    from shapely.geometry import MultiPoint
    com, mass, feet = np.zeros(3), 0.0, []
    for p in panels:
        for g in polys(p["g"]):
            c = g.centroid
            X = p["c"] * p["n"] + (c.x / k) * p["u"] + (c.y / k) * p["v"]
            com += X * g.area
            mass += g.area
            ring = np.array(g.exterior.coords) / k
            W = p["c"] * p["n"] + ring[:, :1] * p["u"] + ring[:, 1:2] * p["v"]
            feet.append(W[W[:, 2] < 0.1][:, :2])
    feet = np.concatenate(feet) if feet else np.zeros((0, 2))
    if mass == 0 or len(feet) < 3:
        return False, None
    com /= mass
    hull = MultiPoint(feet).convex_hull
    inside = hull.contains(Point(com[:2]))
    return bool(inside), float(hull.exterior.distance(Point(com[:2])) * k) if hull.geom_type == "Polygon" else None
