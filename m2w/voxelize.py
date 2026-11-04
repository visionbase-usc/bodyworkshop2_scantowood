"""Mesh -> voxel solid.

Scanned meshes are rarely watertight, so nothing here trusts the mesh to be closed:
the surface is rasterised, thickened a little to seal small holes, and whatever the
outside cannot reach counts as solid.
"""
import numpy as np
import trimesh
from scipy import ndimage as ndi

UNIT_LONGEST = 6.0   # the longest side in design units; every default below is tuned to this size
VOXEL = 0.025        # design units


def load_mesh(path, up="z"):
    """Load any mesh trimesh can read, rotate it to z-up, sit it on z = 0, scale to design units."""
    m = trimesh.load(path, force="mesh", process=False)
    if not isinstance(m, trimesh.Trimesh) or len(m.faces) == 0:
        raise ValueError("檔案裡沒有 mesh（三角面）。3DGS 的 .ply 只有點，要先轉成 mesh。/ メッシュ（三角面）がない。3DGS の .ply は点だけなので、先にメッシュに変換する")
    v = np.asarray(m.vertices, float)
    if up == "auto":   # OBJ and glTF are y-up by convention, STL and PLY z-up
        up = "y" if str(path).lower().endswith((".obj", ".glb", ".gltf")) else "z"
    axis = up.lstrip("+-").lower()
    sign = -1.0 if up.startswith("-") else 1.0
    if axis == "x":
        v = np.stack([v[:, 1], v[:, 2], v[:, 0]], 1)
    elif axis == "y":
        v = np.stack([v[:, 2], v[:, 0], v[:, 1]], 1)
    elif axis != "z":
        raise ValueError(f"up_axis 只能是 x、y、z（可加負號）: {up}")
    if sign < 0:
        v = v * [1, -1, -1]
    lo, hi = v.min(0), v.max(0)
    longest = float((hi - lo).max())
    if longest <= 0:
        raise ValueError("mesh 沒有大小 / メッシュのサイズがゼロ")
    v = (v - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]) * (UNIT_LONGEST / longest)
    return v, np.asarray(m.faces), up


def surface_points(v, f, spacing, max_points=30_000_000, seed=0):
    """Points on every triangle, about `spacing` apart."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    per_tri = np.ceil(area / spacing ** 2).astype(np.int64) + 1
    if per_tri.sum() > max_points:
        per_tri = np.maximum((per_tri * (max_points / per_tri.sum())).astype(np.int64), 1)
    idx = np.repeat(np.arange(len(f)), per_tri.astype(np.intp))
    rng = np.random.default_rng(seed)
    r1, r2 = np.sqrt(rng.random(len(idx))), rng.random(len(idx))
    return ((1 - r1)[:, None] * a[idx] + (r1 * (1 - r2))[:, None] * b[idx] + (r1 * r2)[:, None] * c[idx])


def voxelize(v, f, h=VOXEL, seal=1):
    """Solid voxels. Returns (occ, origin). `seal` voxels of thickening close small holes."""
    pad = seal + 3
    origin = v.min(0) - pad * h
    shape = np.ceil((v.max(0) - v.min(0)) / h).astype(int) + 2 * pad + 1
    occ = np.zeros(shape, bool)
    idx = np.floor((surface_points(v, f, h / 2) - origin) / h).astype(np.int64)
    occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    wall = ndi.binary_dilation(occ, iterations=seal)
    lab, _ = ndi.label(~wall)
    outside = lab == lab[0, 0, 0]
    # scans are often open, usually at the bottom, and then the outside leaks in. A voxel
    # with the surface on at least 5 of its 6 sides counts as inside anyway.
    sides = np.zeros(wall.shape, np.int8)
    for ax in range(3):
        sides += np.logical_or.accumulate(wall, axis=ax)
        sides += np.flip(np.logical_or.accumulate(np.flip(wall, ax), axis=ax), ax)
    solid = ~outside | (sides >= 5)
    if seal:
        # undo the thickening, but never lose the surface itself
        solid = ndi.binary_erosion(solid, iterations=seal) | occ
    return solid, origin


def main_component(solid):
    lab, _ = ndi.label(solid)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    return lab == sz.argmax()


def envelope(solid, h, R, keep_bottom=0.15):
    """Morphological closing at radius R. Bigger R = more abstract, closer to one mass."""
    if R <= 0:
        return solid
    r = R / h
    pad = int(np.ceil(r)) + 2
    s = np.pad(solid, pad)
    dil = ndi.distance_transform_edt(~s) <= r
    clo = (ndi.distance_transform_edt(dil) > r)[pad:-pad, pad:-pad, pad:-pad]
    # closing would weld feet together across the ground; keep the bottom layer as it was
    z0 = np.argwhere(solid.any((0, 1)))[0, 0]
    kb = z0 + int(keep_bottom / h)
    clo[:, :, :kb] = solid[:, :, :kb]
    return clo | solid


def crop(occ, margin=3):
    w = np.argwhere(occ)
    lo = np.maximum(w.min(0) - margin, 0)
    hi = np.minimum(w.max(0) + margin + 1, occ.shape)
    return occ[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]], lo


def voxels_to_mesh(occ, h, origin, smooth_sigma=1.0, smooth_iters=5):
    from skimage import measure
    f = ndi.gaussian_filter(np.pad(occ, 2).astype(np.float32), smooth_sigma)
    if f.max() <= 0.5:      # too thin to survive the blur
        f = np.pad(occ, 2).astype(np.float32)
    v, faces, _, _ = measure.marching_cubes(f, 0.5, spacing=(h, h, h))
    v = v - 2 * h + np.asarray(origin)
    m = trimesh.Trimesh(v, faces[:, ::-1], process=True)
    if smooth_iters:
        trimesh.smoothing.filter_taubin(m, iterations=smooth_iters)
    return m
