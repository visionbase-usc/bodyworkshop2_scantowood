"""Panel outlines and voids.

Material that must stay: a band along the outline, ribs around the slots and stick holes,
and pads where the panel touches the ground. Everything else may open up. Free area is split
into Voronoi cells from Poisson-disk seeds, then each cell is shrunk and rounded into a void,
which produces the cellular 'web' look. Voids only open where the volume is thick across the
panel, so panels that stand in for a thin part of the volume stay solid.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.draw import polygon as fill_polygon


def _disk(r):
    r = max(int(round(r)), 1)
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def thickness_across(e, vol, max_t=1.5):
    """Contiguous volume thickness through each panel pixel along the panel normal."""
    ij = np.argwhere(e.mask)
    X = e.pix_to_world(ij)
    t = np.zeros(len(X))
    for sign in (1, -1):
        inside = np.ones(len(X), bool)
        for d in np.arange(vol.h, max_t / 2 + vol.h, vol.h):
            inside &= vol.lookup(X + sign * d * e.n)
            t += inside * vol.h
    out = np.zeros(e.mask.shape)
    out[ij[:, 0], ij[:, 1]] = t
    return out


def poisson_seeds(region, spacing_px, rng):
    pts = np.argwhere(region)
    if not len(pts):
        return np.zeros((0, 2))
    pts = pts[rng.permutation(len(pts))]
    chosen, tree = [], None
    for p in pts[: max(2000, len(pts) // 20)]:
        if chosen and tree.query(p)[0] < spacing_px:
            continue
        chosen.append(p)
        tree = cKDTree(chosen)
    return np.array(chosen, float)


def outline_mask(e, smooth=1.5):
    return ndi.gaussian_filter(e.mask.astype(float), smooth) > 0.5


def rasterize(geoms, e, k):
    """Shapely polygons (plane millimetres) -> mask on the panel raster."""
    m = np.zeros(e.mask.shape, bool)
    for g in geoms:
        for p in getattr(g, "geoms", [g]):
            c = (np.asarray(p.exterior.coords) / k - e.uv0) / e.px - 0.5
            r, cc = fill_polygon(c[:, 0], c[:, 1], m.shape)
            m[r, cc] = True
    return m


def void_mask(e, vol, R, keep_out, band=0.05, rib=0.06, keep_rib=0.05, foot=0.12, cell=0.42,
              min_void=0.012, thick_min=0.2, seed=0):
    """Where the panel opens up. `keep_out` marks slots and holes: voids stay clear of them."""
    px = e.px
    rng = np.random.default_rng(seed + e.order)
    ij = np.argwhere(R)
    low = ij[e.pix_to_world(ij)[:, 2] < 0.08]
    F = np.zeros_like(R)
    F[low[:, 0], low[:, 1]] = True
    keep = R & ~ndi.binary_erosion(R, _disk(band / px))
    keep |= ndi.binary_dilation(keep_out, _disk(keep_rib / px)) & R
    keep |= ndi.binary_dilation(F, _disk(foot / px)) & R
    t = thickness_across(e, vol)
    free = R & ~keep & (ndi.gaussian_filter(t, 2) >= thick_min)
    free = ndi.binary_opening(free, _disk(rib / 2 / px))
    voids = np.zeros_like(R)
    if not free.any():
        return voids
    S = poisson_seeds(free, cell / px, rng)
    if not len(S):
        return voids
    ij = np.argwhere(free)
    lab = np.zeros(R.shape, int)
    lab[ij[:, 0], ij[:, 1]] = cKDTree(S).query(ij)[1] + 1
    # cell borders become ribs
    hi = np.where(lab == 0, lab.max() + 1, lab)
    border = (ndi.grey_dilation(lab, size=3) != ndi.grey_erosion(hi, size=3)) & free
    inner = free & ~ndi.binary_dilation(border, _disk(rib / 2 / px))
    inner = ndi.binary_opening(inner, _disk(rib / 2 / px))
    inner = ndi.gaussian_filter(inner.astype(float), 2.0) > 0.5
    cl, nc = ndi.label(inner)
    if nc:
        areas = ndi.sum(np.ones_like(cl), cl, index=np.arange(1, nc + 1)) * px * px
        voids = np.isin(cl, np.flatnonzero(areas >= min_void) + 1)
    return voids & free
