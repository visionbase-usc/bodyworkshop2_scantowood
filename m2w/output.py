"""Write the results: DXF per sheet, preview image, 3D viewer, report."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
LAYERS = {"CUT_OUTER": 1, "CUT_INNER": 5, "LABEL": 7, "SHEET": 8}


def write_dxf(placed, n_sheets, cfg, out):
    import ezdxf
    from ezdxf import units
    from .joinery import label_point
    W, H = cfg["sheet_mm"]
    files = []
    for si in range(n_sheets):
        doc = ezdxf.new("R2010", setup=True)
        doc.units = units.MM
        doc.header["$MEASUREMENT"] = 1
        for name, color in LAYERS.items():
            doc.layers.add(name, color=color)
        msp = doc.modelspace()
        msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs={"layer": "SHEET"})
        for q in placed:
            if q["sheet"] != si:
                continue
            g = q["placed"]
            msp.add_lwpolyline(list(g.exterior.coords)[:-1], close=True, dxfattribs={"layer": "CUT_OUTER"})
            for ring in g.interiors:
                msp.add_lwpolyline(list(ring.coords)[:-1], close=True, dxfattribs={"layer": "CUT_INNER"})
            p = label_point(g)
            msp.add_text(q["name"], height=cfg["label_height_mm"], dxfattribs={"layer": "LABEL"}).set_placement(
                (p.x, p.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        f = out / f"sheet_{si + 1:02d}.dxf"
        doc.saveas(f)
        files.append(f)
    return files


def draw_sheets(placed, n_sheets, cfg, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP, Rectangle
    from .joinery import label_point
    W, H = cfg["sheet_mm"]
    f, axes = plt.subplots(n_sheets, 1, figsize=(10, (10 * H / W + 0.35) * n_sheets), dpi=150, squeeze=False)
    for si, ax in enumerate(axes[:, 0]):
        ax.add_patch(Rectangle((0, 0), W, H, fc="#faf7f1", ec="#999999", lw=0.8))
        for q in placed:
            if q["sheet"] != si:
                continue
            g = q["placed"]
            ax.add_patch(MP(np.array(g.exterior.coords), fc="#d9b382", ec="#c0392b", lw=0.7))
            for r in g.interiors:
                ax.add_patch(MP(np.array(r.coords), fc="#faf7f1", ec="#2471a3", lw=0.6))
            p = label_point(g)
            ax.text(p.x, p.y, q["name"], ha="center", va="center", fontsize=8, weight="bold")
        ax.set_title(f"sheet {si + 1} / {n_sheets}   {W} x {H} mm   t = {cfg['thickness_mm']} mm", fontsize=9, loc="left")
        ax.set_xlim(-10, W + 10)
        ax.set_ylim(-10, H + 10)
        ax.set_aspect("equal")
        ax.axis("off")
    f.tight_layout()
    f.savefig(path)
    plt.close(f)


def _poly_json(g, s):
    r = lambda c: np.round(np.asarray(c)[:-1] * s, 5).tolist()
    return {"outer": r(g.exterior.coords), "holes": [r(h.coords) for h in g.interiors]}


def write_viewer(panels, parts, ghost, cfg, title, stats, path):
    """Standalone HTML, works offline. Shows the parts as cut, slots included. Metres."""
    k = cfg["_k"]
    m = k / 1000
    P = []
    for p in panels:
        mine = [q for q in parts if q["id"] == p["id"]]
        P.append({"id": p["id"], "n": p["n"].tolist(), "c": float(p["c"] * m), "u": p["u"].tolist(), "v": p["v"].tolist(),
                  "polys": [_poly_json(q["geom"], 1e-3) for q in mine],
                  "area_wood": float(sum(q["geom"].area for q in mine) / 1e6)})
    scene = {"title": title, "thickness": cfg["thickness_mm"] / 1000,
             "panels": P,
             "stats": stats, "ghost": {"v": (ghost.vertices * m).round(4).ravel().tolist(), "f": ghost.faces.ravel().tolist()}}
    tpl = (HERE / "viewer_template.html").read_text(encoding="utf-8")
    vendor = "".join(f"<script>{(HERE / 'vendor' / n).read_text(encoding='utf-8')}</script>\n" for n in ("three.min.js", "OrbitControls.js"))
    html = tpl.replace("<!--VENDOR-->", vendor).replace("__SCENE__", json.dumps(scene, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    path.write_text(html, encoding="utf-8")


def write_report(r, path, lang=None):
    if lang == "en":
        return write_english_report(r, path)
    L = [f"# 木構報告 / 木構造レポート：{r['name']}", ""]
    L += [f"- 尺寸 / サイズ：{r['size'][0]:.0f} × {r['size'][1]:.0f} × {r['size'][2]:.0f} mm",
          f"- 木板 / 板：{r['n_panels']} 片（零件 {r['n_parts']} 個）",
          f"- 板材 / 使用板：{r['n_sheets']} 張 {r['sheet'][0]} × {r['sheet'][1]} mm，板厚 {r['thickness']} mm",
          f"- 卡榫 / 相欠き：{r['n_joints']} 處；斜交最小 {r['min_angle']:.0f}°",
          f"- 刀徑 / 刃物径：{r['tool']} mm，公差 {r['tolerance']} mm",
          f"- 站得穩嗎 / 自立するか：{'可以，重心在落地範圍內（估算）' if r['stable'] else '不行，重心在落地範圍外（估算）'}", ""]
    if r["warnings"]:
        L += ["## 要注意 / 注意", ""] + [f"- {w}" for w in r["warnings"]] + [""]
    L += ["## 組裝順序 / 組み立て順", "", "由上往下插，照這個順序：", "上から差し込む。順番：", ""]
    L += ["→ ".join(f"P{i:02d}" for i in r["order"]), ""]
    L += ["## 卡榫 / 相欠き", "", "| 先放 | 後放 | 夾角 | 槽寬 mm | 接觸長 mm |", "|---|---|---|---|---|"]
    L += [f"| P{j['early']:02d} | P{j['late']:02d} | {j['angle']:.0f}° | {j['width']:.1f} | {j['length']:.0f} |" for j in r["joints"]]
    L += [""]
    L += ["## DXF 圖層 / レイヤー", "", "| 圖層 | 內容 |", "|---|---|",
          "| CUT_OUTER | 零件外框（含卡榫的槽）/ 外形（溝を含む） |", "| CUT_INNER | 內孔 / 内側の穴 |",
          "| LABEL | 零件編號 / 部品番号 |", "| SHEET | 板材邊界（不要切）/ 板の外周（切らない） |", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def write_english_report(r, path):
    stability = ("Yes: the center of mass is within the support footprint (estimate)." if r["stable"]
                 else "No: the center of mass is outside the support footprint (estimate).")
    lines = [f"# Assembly report: {r['name']}", "",
             f"- Dimensions: {r['size'][0]:.0f} × {r['size'][1]:.0f} × {r['size'][2]:.0f} mm",
             f"- Panels: {r['n_panels']} ({r['n_parts']} parts)",
             f"- Sheets: {r['n_sheets']} sheets, {r['sheet'][0]} × {r['sheet'][1]} mm; thickness {r['thickness']} mm",
             f"- Joints: {r['n_joints']}; minimum intersection angle {r['min_angle']:.0f}°",
             f"- Tool diameter: {r['tool']} mm; joint tolerance: {r['tolerance']} mm",
             f"- Can it stand on its own? {stability}", ""]
    if r["warnings_en"]:
        lines += ["## Warnings", ""] + [f"- {w}" for w in r["warnings_en"]] + [""]
    lines += ["## Assembly order", "", "Insert the panels from above in this order:", "",
              " → ".join(f"P{i:02d}" for i in r["order"]), "",
              "## Joints", "", "| Insert first | Insert next | Angle | Slot width (mm) | Contact length (mm) |",
              "|---|---|---|---|---|"]
    lines += [f"| P{j['early']:02d} | P{j['late']:02d} | {j['angle']:.0f}° | {j['width']:.1f} | {j['length']:.0f} |"
              for j in r["joints"]]
    lines += ["", "## DXF layers", "", "| Layer | Description |", "|---|---|",
              "| CUT_OUTER | Part outlines, including joint slots |", "| CUT_INNER | Interior holes |",
              "| LABEL | Part numbers |", "| SHEET | Sheet boundary — do not cut |", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
