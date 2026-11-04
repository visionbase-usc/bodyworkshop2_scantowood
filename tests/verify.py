"""把切好的零件在 3D 裡組起來，檢查做不做得出來。不依賴 mesh2wood 算出來的卡榫資料，只看最後的形狀。

1. 組好的狀態：任兩片板的實體不能互相穿插。
2. 插入：照組裝順序，每一片沿著卡榫方向從上面滑進去，一路上不能撞到已經放好的板。
3. 木條不能穿過板的實體（孔要夠大）。
4. DXF 重新讀回來：只有封閉線、都在板材範圍內、零件不重疊、單位是 mm。

    python tests/verify.py 我的模型.stl [--size 800]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import argparse

import ezdxf
import numpy as np
from manifold3d import CrossSection, FillRule, Manifold
from shapely.geometry import Polygon

import mesh2wood as M
from m2w.joinery import polys, strip_frame


def solid(part, panel, t):
    """Extruded part in millimetres, world coordinates."""
    k = CFG["_k"]
    g = part["geom"]
    rings = [np.asarray(r.coords)[:-1] for r in [g.exterior, *g.interiors]]
    m = Manifold.extrude(CrossSection(rings, FillRule.EvenOdd), t)
    T = np.zeros((3, 4))
    T[:, 0], T[:, 1], T[:, 2] = panel["u"], panel["v"], panel["n"]
    T[:, 3] = panel["n"] * (panel["c"] * k - t / 2)
    return m.transform(T)


def overlap(a, b):
    return (a ^ b).volume()


ap = argparse.ArgumentParser()
ap.add_argument("mesh")
ap.add_argument("--size", type=float)
ap.add_argument("--up")
ap.add_argument("--out")
ap.add_argument("--strips", type=int)
ap.add_argument("--panels", type=int)
ap.add_argument("--abstraction", type=float)
ap.add_argument("--thickness", type=float)
ap.add_argument("--no-holes", action="store_true")
a = ap.parse_args()
sys.stdout.reconfigure(encoding="utf-8")
CFG = M.load_settings(M.HERE / "settings.json", a)
try:
    res = M.run(a.mesh, CFG, a.out, log=lambda s: None)
except ValueError as e:
    print("錯誤訊息：", e)
    sys.exit(2)
t, rep = CFG["thickness_mm"], res["report"]
by_id = {p["id"]: p for p in res["panels"]}
solids = {}
for q in res["parts"]:
    solids.setdefault(q["id"], []).append(solid(q, by_id[q["id"]], t))
fails = []

# 1 ----------------------------------------------------------- assembled state
ids = list(solids)
worst = 0.0
for i, A in enumerate(ids):
    for B in ids[i + 1:]:
        v = sum(overlap(x, y) for x in solids[A] for y in solids[B])
        worst = max(worst, v)
        if v > 1.0:
            fails.append(f"P{A:02d} 和 P{B:02d} 互相穿插 {v:.0f} mm³")
print(f"1. 組好的狀態：最大穿插 {worst:.2f} mm³")

# 2 ----------------------------------------------------------- slide in, in order
order = rep["order"]
jd = {}
for j in rep["joints"]:
    jd.setdefault(j["late"], []).append((j["early"], np.array(j["up"])))
blocked = 0
for i, pid in enumerate(order):
    placed_before = order[:i]
    dirs = [d for e, d in jd.get(pid, []) if e in placed_before]
    if not dirs:
        continue
    d = np.mean(dirs, 0)
    d /= np.linalg.norm(d)
    spread = max(np.degrees(np.arccos(np.clip(x @ d, -1, 1))) for x in dirs)
    hit = 0.0
    for dist in np.arange(10, 1.2 * CFG["size_mm"], 25):
        for m in solids[pid]:
            mv = m.translate(d * dist)
            for e in placed_before:
                for o in solids[e]:
                    hit = max(hit, overlap(mv, o))
    if hit > 1.0:
        blocked += 1
        print(f"   P{pid:02d} 插入時撞到（{hit:.0f} mm³，卡榫方向差 {spread:.0f}°）")
print(f"2. 插入：{len(order)} 片，{blocked} 片會撞到")
if blocked:
    fails.append(f"{blocked} 片插入時會撞到")

# 3 ----------------------------------------------------------- sticks
k = CFG["_k"]
sw, sh = CFG["strip_section_mm"]
worst = 0.0
n_strip = 0
for s in res["strips"]:
    p0, p1 = np.asarray(s["a"]) * k, np.asarray(s["b"]) * k
    L = np.linalg.norm(p1 - p0)
    d = (p1 - p0) / L
    e1, e2 = strip_frame(d)
    T = np.zeros((3, 4))
    T[:, 0], T[:, 1], T[:, 2], T[:, 3] = e1, e2, d, (p0 + p1) / 2
    box = Manifold.cube((sw, sh, L), True).transform(T)
    n_strip += 1
    for pid in ids:
        for m in solids[pid]:
            v = overlap(box, m)
            worst = max(worst, v)
            if v > 1.0:
                fails.append(f"木條 S{n_strip:02d} 撞到 P{pid:02d}（{v:.0f} mm³）")
print(f"3. 木條：{n_strip} 根，最大穿插 {worst:.2f} mm³")

# 4 ----------------------------------------------------------- DXF read back
W, H = CFG["sheet_mm"]
n_ent = 0
for f in res["files"]:
    doc = ezdxf.readfile(f)
    assert doc.units == 4, "DXF 單位不是 mm"
    outers = []
    for e in doc.modelspace():
        if e.dxftype() == "LWPOLYLINE":
            n_ent += 1
            if not e.closed:
                fails.append(f"{f.name} 有沒封閉的線")
            pts = np.array([p[:2] for p in e.get_points()])
            if e.dxf.layer != "SHEET" and (pts.min() < 0 or pts[:, 0].max() > W or pts[:, 1].max() > H):
                fails.append(f"{f.name} 有線超出板材")
            if e.dxf.layer == "CUT_OUTER":
                outers.append(Polygon(pts).buffer(0))
    for i, A in enumerate(outers):
        for B in outers[i + 1:]:
            if A.intersection(B).area > 1:
                fails.append(f"{f.name} 零件重疊")
print(f"4. DXF：{len(res['files'])} 個檔，{n_ent} 條封閉線")

print(f"\n{rep['n_panels']} 片板、{rep['n_joints']} 處卡榫、{rep['n_sheets']} 張板材；站得穩：{rep['stable']}")
for w in rep["warnings"]:
    print("注意：", w)
print("驗證：" + ("全部通過" if not fails else "失敗"))
for x in fails[:12]:
    print("  ✗", x)
sys.exit(1 if fails else 0)
