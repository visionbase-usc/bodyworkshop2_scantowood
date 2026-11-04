"""mesh2wood: 丟一個 mesh 進來，算出可以用 CNC 切的木構。

    python mesh2wood.py 我的模型.stl
    python mesh2wood.py 我的模型.stl --size 800 --strips 0

參數在 settings.json，說明見 README.md。結果放在 mesh 旁邊的「<檔名>_wood」資料夾。
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from m2w.construct import Volume, select_panels, select_strips
from m2w.joinery import (best_order, cut_joints, find_contacts, joint_spread, loose_parts, make_parts,
                         mask_to_geom, nest, polys, stability, strip_holes, tool_safe)
from m2w.output import draw_sheets, write_dxf, write_report, write_viewer
from m2w.stylize import outline_mask, rasterize, void_mask
from m2w.voxelize import (UNIT_LONGEST, VOXEL, crop, envelope, load_mesh, main_component,
                          voxelize, voxels_to_mesh)

HERE = Path(__file__).parent
TOO_THIN = ("選不出木板：物體太薄或太細。如果它是平躺的，把 up_axis 換一個軸試試，或調高 abstraction。"
            "/ 板が選べない。物体が薄すぎる。up_axis を変えるか abstraction を上げる")


def load_settings(path, args):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for key, name in (("size", "size_mm"), ("up", "up_axis"), ("strips", "strips"), ("panels", "max_panels"),
                      ("abstraction", "abstraction"), ("thickness", "thickness_mm")):
        if getattr(args, key) is not None:
            cfg[name] = getattr(args, key)
    if args.no_holes:
        cfg["holes"] = False
    return cfg


def run(mesh_path, cfg, out=None, log=print):
    T = time.time()
    step = lambda s: log(f"[{time.time() - T:5.0f} 秒] {s}")
    mesh_path = Path(mesh_path)
    out = Path(out) if out else mesh_path.with_name(mesh_path.stem + "_wood")
    out.mkdir(parents=True, exist_ok=True)
    k = cfg["size_mm"] / UNIT_LONGEST          # mm per design unit
    cfg["_k"] = k
    tool, t = cfg["tool_diameter_mm"], cfg["thickness_mm"]
    warnings = []

    step("讀取 mesh / メッシュを読み込み")
    v, f, up = load_mesh(mesh_path, cfg["up_axis"])
    size = (v.max(0) - v.min(0)) * k
    log(f"  {len(f):,} 個三角面，{up} 軸朝上，尺寸 {size[0]:.0f} × {size[1]:.0f} × 高 {size[2]:.0f} mm")
    if size[2] < 0.5 * size[:2].max():
        warnings.append(f"高度只有 {size[2]:.0f} mm，物體可能是躺著的（目前 {up} 軸朝上）。不對的話改 up_axis。"
                        f"/ 物体が寝ているかもしれない（{up} 軸が上）。up_axis を変更")

    step("算出體積 / 体積を計算")
    solid, origin = voxelize(v, f)
    solid = main_component(solid)
    env = envelope(solid, VOXEL, cfg["abstraction"] * UNIT_LONGEST)
    env, off = crop(env)
    origin = origin + off * VOXEL
    vol = Volume(env, VOXEL, origin)

    step("選木板 / 板を選ぶ")
    els = select_panels(vol, delta=cfg["panel_spacing"], max_panels=cfg["max_panels"], target_coverage=cfg["coverage"],
                        max_tilt_deg=cfg["max_tilt_deg"], log=log)
    if not els:
        raise ValueError(TOO_THIN)
    step("畫外框 / 外形")
    panels, kept = [], []
    for e in els:
        R = outline_mask(e)
        g = mask_to_geom(R, e.px, e.uv0, k)
        g = polys(tool_safe(g, tool)) if g is not None else []
        if g:
            panels.append(dict(id=len(panels) + 1, n=e.n, c=e.c, u=e.u, v=e.v, g=max(g, key=lambda p: p.area), e=e, R=R))
            kept.append(e)

    if not panels:
        raise ValueError(TOO_THIN)

    if len(panels) < 2:
        warnings.append("只算出一片板，沒有構築可言。物體可能太細，試試調高 abstraction。/ 板が1枚だけ。abstraction を上げる")

    step("卡榫、木條 / 相欠きと角材")
    contacts = find_contacts(panels, k, t)
    order, blocked = best_order([p["id"] for p in panels], contacts)
    slots, joint_of, joints = cut_joints(panels, contacts, order, cfg)
    strips = select_strips(vol, kept, n_strips=cfg["strips"] * 4, log=lambda s: None)
    holes, strips = strip_holes(panels, strips, cfg, cfg["strips"], log=log)
    log(f"  {len(joints)} 處卡榫，{len(strips)} 根木條")
    if blocked:
        warnings.append("有木板找不到不會撞到的組裝順序，要再檢查。/ ぶつからない組み立て順が見つからない板がある")
    spread = joint_spread(joints)
    if spread > 3:
        warnings.append(f"木板不是全部垂直，卡榫方向差到 {spread:.0f}°，可能插不進去。把 max_tilt_deg 改回 0 就一定插得進去。"
                        "/ 溝の向きが揃っていない。max_tilt_deg を 0 に")

    step("開洞 / 穴")
    band = max(0.05, 2 * tool / k)
    rib = max(0.06, 2 * tool / k)
    for p in panels:
        if not cfg["holes"]:
            break
        keep_out = rasterize(slots[p["id"]] + holes[p["id"]], p["e"], k)
        V = void_mask(p["e"], vol, p["R"], keep_out, band=band, rib=rib, keep_rib=band, cell=cfg["hole_size"],
                      min_void=max(0.012, (3 * tool / k) ** 2))
        vg = mask_to_geom(V, p["e"].px, p["e"].uv0, k) if V.any() else None
        if vg is not None:
            r = max(tool, 6.0)
            p["g"] = p["g"].difference(vg.buffer(-r, quad_segs=12).buffer(r, quad_segs=12))
    parts, scrap = make_parts(panels, slots, holes, joint_of)
    if tool > min((j["width"] for j in joints), default=tool):
        warnings.append(f"刀徑 {tool} mm 比槽還寬，切不出來。/ 刃物径が溝より太い")
    split = sorted({q["id"] for q in parts if q["name"][-1].isalpha()})
    if split:
        warnings.append("被槽切成兩塊以上的板：" + "、".join(f"P{i:02d}" for i in split) + "。/ 溝で分割された板")
    loose = loose_parts(parts)
    if loose:
        warnings.append("這些零件沒有接到主體，組起來會掉下來：" + "、".join(loose) + "。/ 本体につながっていない部品")
    stable, _ = stability(panels, k)
    if not stable:
        warnings.append("重心在落地範圍外，可能站不住（估算）。可以試試別的 up_axis 或加底座。/ 重心が足元の外（推定）")

    step("排版 / 板取り")
    placed, n_sheets = nest(parts, cfg["sheet_mm"], cfg["sheet_margin_mm"], cfg["part_gap_mm"])

    step("輸出 / 書き出し")
    files = write_dxf(placed, n_sheets, cfg, out)
    draw_sheets(placed, n_sheets, cfg, out / "sheets.png")
    ghost = voxels_to_mesh(env[::2, ::2, ::2], VOXEL * 2, origin, smooth_iters=8)
    strip_rows = [dict(length=s["length"] * k, through=s["pierces"]) for s in strips]
    stats = [["木板", f"{len(panels)} 片"], ["板材", f"{n_sheets} 張"], ["卡榫", f"{len(joints)} 處"],
             ["木條", f"{len(strips)} 根"], ["板厚", f"{t} mm"],
             ["尺寸", f"{size[0]:.0f}×{size[1]:.0f}×{size[2]:.0f}"]]
    write_viewer(panels, parts, strips, ghost, cfg, mesh_path.stem, stats, out / "viewer.html")
    report = dict(name=mesh_path.name, up=up, size=size.tolist(), n_panels=len(panels), n_parts=len(parts), n_sheets=n_sheets,
                  sheet=cfg["sheet_mm"], thickness=t, tool=tool, tolerance=cfg["tolerance_mm"], n_joints=len(joints),
                  min_angle=min((j["angle"] for j in joints), default=90), stable=stable, warnings=warnings, order=order,
                  joints=joints, strips=strip_rows, strip_section=cfg["strip_section_mm"])
    write_report(report, out / "report.md")
    (out / "settings_used.json").write_text(json.dumps({a: b for a, b in cfg.items() if a[0] != "_"}, indent=2), encoding="utf-8")
    step(f"完成 / 完了：{len(panels)} 片板、{len(joints)} 處卡榫、{len(strips)} 根木條、{n_sheets} 張板材")
    for w in warnings:
        log("  注意：" + w)
    log(f"  → {out}")
    return dict(out=out, report=report, panels=panels, parts=parts, placed=placed, files=files, strips=strips)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="mesh → CNC 木構")
    ap.add_argument("mesh", help=".stl .obj .ply .glb")
    ap.add_argument("--settings", default=HERE / "settings.json")
    ap.add_argument("--out", help="輸出資料夾（預設：mesh 旁邊的 <檔名>_wood）")
    ap.add_argument("--size", type=float, help="最長邊 mm")
    ap.add_argument("--up", help="哪個軸朝上：x y z；負方向要寫成 --up=-z")
    ap.add_argument("--strips", type=int, help="木條數量，0 = 不用木條")
    ap.add_argument("--panels", type=int, help="木板數量上限")
    ap.add_argument("--abstraction", type=float, help="抽象程度：0 貼著原物，0.2 接近一整塊")
    ap.add_argument("--thickness", type=float, help="板厚 mm")
    ap.add_argument("--no-holes", action="store_true", help="不開洞")
    a = ap.parse_args()
    try:
        run(a.mesh, load_settings(a.settings, a), a.out)
    except (ValueError, FileNotFoundError) as e:
        print(f"\n錯誤 / エラー：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
