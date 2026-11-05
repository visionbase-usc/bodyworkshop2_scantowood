const TEXT = {
  en: {
    tagline: "Turn a mesh into a CNC-cut wood structure", dropTitle: "Drop a mesh here, or click to choose a file", dropSub: ".stl  .obj  .ply  .glb",
    material: "Materials & machine", size_mm: "Longest side (mm)", thickness_mm: "Board thickness (mm)", tool_diameter_mm: "Tool diameter (mm)", tolerance_mm: "Joint tolerance (mm)",
    sheet_w: "Sheet length (mm)", sheet_h: "Sheet width (mm)", shape: "Shape", up_axis: "Up axis", auto: "Auto",
    abstraction: "Abstraction", abstractionHint: "0 follows the original; higher values simplify the shape", panel_spacing: "Panel spacing", spacingHint: "Smaller values create more panels",
    holes: "Cut holes", strips: "Number of wood strips", strip_mm: "Strip cross-section (mm)", recalc: "Calculate", reset: "Reset defaults",
    privacy: "Everything runs on your computer. Your files are never uploaded.", step1: "Check the board thickness, tool diameter, and sheet size on the left", step2: "Drag a mesh into this window", step3: "Check the 3D view, then download the DXF files",
    tab3d: "3D structure", tabSheet: "Sheet layout", tabReport: "Assembly report", download: "Download all .zip", cancel: "Cancel", failTitle: "Calculation failed",
    loading: "Preparing the calculation engine. The first visit takes about a minute; later visits are much faster.", engineReady: "Calculation engine ready.", engineFail: "Could not load the calculation engine. Check your connection and reload the page.",
    waiting: "Downloading the calculation engine. Calculation will start automatically…", steps: ["Reading mesh", "Computing volume", "Selecting panels", "Drawing outlines", "Joints & wood strips", "Cutting holes", "Sheet layout", "Exporting"],
    memory: "This mesh is too large for the browser's available memory. Reduce it to fewer than 1 million faces and try again, or use the command-line version (see README).",
    fileProtocol: "This page cannot be opened by double-clicking. Use the GitHub Pages URL, or run python -m http.server in the project folder.",
    readFail: "Could not read this file. It may have been moved or changed. Please select it again.", upIs: "The {up} axis is currently pointing up. If the shape looks wrong, change the Up axis on the left and calculate again.", notMesh: "Unsupported file format. Please use .stl, .obj, .ply, or .glb.",
  },
  zh: {
    tagline: "把 mesh 算成可以 CNC 切割的木構", dropTitle: "把 mesh 拖進來，或點這裡選檔案", dropSub: ".stl  .obj  .ply  .glb",
    material: "材料與機器", size_mm: "作品最長邊 mm", thickness_mm: "板厚 mm", tool_diameter_mm: "刀徑 mm", tolerance_mm: "卡榫公差 mm",
    sheet_w: "板材長 mm", sheet_h: "板材寬 mm", shape: "造型", up_axis: "朝上的軸", auto: "自動",
    abstraction: "抽象程度", abstractionHint: "0 貼著原物，越大越像一整塊", panel_spacing: "板的疏密", spacingHint: "越小板越多",
    holes: "開洞", strips: "木條數量", strip_mm: "木條斷面 mm", recalc: "計算", reset: "恢復預設",
    privacy: "全部在你的電腦上計算，檔案不會上傳。", step1: "確認左邊的板厚、刀徑、板材是你們實際用的", step2: "把 mesh 拖進這個視窗", step3: "看 3D，滿意就下載 DXF",
    tab3d: "3D 木構", tabSheet: "分料", tabReport: "組裝報告", download: "全部下載 .zip", cancel: "取消", failTitle: "算不出來",
    loading: "正在準備計算引擎。第一次約需 1 分鐘，之後會快很多。", engineReady: "計算引擎準備好了。", engineFail: "計算引擎載入失敗，請確認網路後重新整理。",
    waiting: "計算引擎還在下載，好了會自動開始…", steps: ["讀取 mesh", "算出體積", "選木板", "畫外框", "卡榫與木條", "開洞", "排版", "輸出"],
    memory: "這個 mesh 太大，瀏覽器的記憶體不夠。請先減面到 100 萬面以下再試，或改用指令版（見 README）。",
    fileProtocol: "這個頁面不能直接雙擊打開，請用 GitHub Pages 的網址，或在資料夾裡執行 python -m http.server。",
    readFail: "讀不到這個檔案，可能被移動或改過了。請重新選一次。", upIs: "目前 {up} 軸朝上。形狀不對的話，改左邊的「朝上的軸」再算一次。", notMesh: "不支援這個檔案格式，請用 .stl .obj .ply .glb。",
  },
  ja: {
    tagline: "メッシュを CNC で切れる木構造に計算する", dropTitle: "メッシュをドラッグ、またはクリックして選択", dropSub: ".stl  .obj  .ply  .glb",
    material: "材料と機械", size_mm: "作品の最長辺 mm", thickness_mm: "板厚 mm", tool_diameter_mm: "刃物径 mm", tolerance_mm: "相欠き公差 mm",
    sheet_w: "板の長さ mm", sheet_h: "板の幅 mm", shape: "形", up_axis: "上向きの軸", auto: "自動",
    abstraction: "抽象度", abstractionHint: "0 は元の形に沿う。大きいほど塊に近い", panel_spacing: "板の密度", spacingHint: "小さいほど板が増える",
    holes: "穴を開ける", strips: "角材の本数", strip_mm: "角材の断面 mm", recalc: "計算", reset: "初期値に戻す",
    privacy: "計算はすべてこのパソコンの中で行い、ファイルはアップロードされない。", step1: "左の板厚・刃物径・板のサイズを実際の値にする", step2: "メッシュをこのウィンドウにドラッグ", step3: "3D を確認し、DXF をダウンロード",
    tab3d: "3D", tabSheet: "板取り", tabReport: "組み立てレポート", download: "すべてダウンロード .zip", cancel: "キャンセル", failTitle: "計算できなかった",
    loading: "計算エンジンを準備中。初回は約1分かかる。", engineReady: "計算エンジンの準備完了。", engineFail: "計算エンジンを読み込めない。ネットワークを確認して再読み込みする。",
    waiting: "計算エンジンをダウンロード中。完了すると自動で始まる…", steps: ["メッシュを読み込み", "体積を計算", "板を選ぶ", "外形", "相欠きと角材", "穴", "板取り", "書き出し"],
    memory: "メッシュが大きすぎて、ブラウザのメモリが足りない。100万面以下に減らすか、コマンド版を使う（README 参照）。",
    fileProtocol: "このページはダブルクリックでは開けない。GitHub Pages の URL を使うか、フォルダで python -m http.server を実行する。",
    readFail: "ファイルを読めない。移動または変更された可能性がある。もう一度選ぶ。", upIs: "現在 {up} 軸が上。形がおかしいときは左の「上向きの軸」を変えて再計算する。", notMesh: "このファイル形式には対応していない。.stl .obj .ply .glb を使う。",
  },
};
const FORMATS = /\.(stl|obj|ply|glb)$/i;
const STORE = "mesh2wood.settings.v1";
const $ = (id) => document.getElementById(id);
const form = $("form");

const store = {   // a convenience only: everything works without it
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  drop(k) { try { localStorage.removeItem(k); } catch {} },
};

const savedLang = store.get("mesh2wood.lang");
const browserLang = navigator.language.split("-")[0];
let lang = Object.hasOwn(TEXT, savedLang) ? savedLang : (Object.hasOwn(TEXT, browserLang) ? browserLang : "zh");
const t = (k) => TEXT[lang][k];
function applyLang() {
  document.documentElement.lang = lang === "zh" ? "zh-Hant" : lang;
  document.querySelectorAll("[data-t]").forEach((el) => { if (!(el.id === "dropTitle" && file) && !(el.id === "dropSub" && file)) el.textContent = t(el.dataset.t); });
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  showEngine();
  if (pending) $("busyTitle").textContent = engine === "ready" ? t("steps")[Math.max(0, Math.min(steps - 1, 7))] : t("waiting");
  if (lastReport) showNotes(lastReport);
}

// ---- settings
let defaults = null;
function fill(c) {
  for (const k of ["size_mm", "thickness_mm", "tool_diameter_mm", "tolerance_mm", "up_axis", "abstraction", "panel_spacing", "strips"]) form[k].value = c[k];
  form.sheet_w.value = c.sheet_mm[0];
  form.sheet_h.value = c.sheet_mm[1];
  form.holes.checked = c.holes;
  form.strip_mm.value = c.strip_section_mm[0];
  syncSliders();
}
function read() {
  const n = (k) => Number(form[k].value);
  return { ...defaults, size_mm: n("size_mm"), thickness_mm: n("thickness_mm"), tool_diameter_mm: n("tool_diameter_mm"), tolerance_mm: n("tolerance_mm"),
    sheet_mm: [n("sheet_w"), n("sheet_h")], up_axis: form.up_axis.value, abstraction: n("abstraction"), panel_spacing: n("panel_spacing"),
    holes: form.holes.checked, strips: n("strips"), strip_section_mm: [n("strip_mm"), n("strip_mm")] };
}
function syncSliders() {
  form.querySelectorAll("input[type=range]").forEach((r) => { r.closest("label").querySelector("output").textContent = Number(r.value).toFixed(2); });
}

// ---- engine
let worker = null, engine = "loading", pending = null, file = null, steps = 0;
function showEngine() {
  const el = $("engine");
  if (location.protocol === "file:") { el.textContent = t("fileProtocol"); return; }
  el.textContent = t({ loading: "loading", ready: "engineReady", failed: "engineFail" }[engine]);
}
function startWorker() {
  if (location.protocol === "file:") return;
  engine = "loading";
  showEngine();
  worker = new Worker("web/worker.js");
  worker.onmessage = onWorker;
  worker.onerror = () => { engine = "failed"; showEngine(); if (pending) fail(t("engineFail")); };
}
function onWorker({ data: m }) {
  if (m.type === "ready") { engine = "ready"; showEngine(); if (pending) $("busyTitle").textContent = t("steps")[0]; }
  else if (m.type === "failed") { engine = "failed"; showEngine(); if (pending) fail(t("engineFail")); }
  else if (m.type === "log") onLog(m.line);
  else if (m.type === "done") finish(m);
  else if (m.type === "error") fail(m.message === "memory" ? t("memory") : m.message);
}
function restart() {
  worker?.terminate();
  startWorker();
}

// ---- running
function panes(show) {
  for (const id of ["empty", "busy", "fail", "view", "sheet", "report"]) $(id).hidden = id !== show;
}
async function run() {
  if (!file) return;
  const cfg = read();
  store.set(STORE, cfg);
  setResult(false);
  panes("busy");
  steps = 0;
  $("log").textContent = "";
  $("bar").value = 0;
  $("busyTitle").textContent = engine === "ready" ? t("steps")[0] : t("waiting");
  $("go").disabled = true;
  pending = true;
  if (engine === "failed") restart();   // the old worker is gone: try again, a second failure lands in fail()
  let bytes;
  try {
    bytes = await file.arrayBuffer();
  } catch {      // moved, renamed or edited since it was chosen
    file = null;
    $("dropTitle").textContent = t("dropTitle");
    $("dropSub").textContent = t("dropSub");
    fail(t("readFail"));
    return;
  }
  worker.postMessage({ name: file.name, bytes, cfg }, [bytes]);
}
function onLog(line) {
  const log = $("log");
  log.textContent += line + "\n";
  log.scrollTop = log.scrollHeight;
  if (line.startsWith("[")) {
    $("bar").value = Math.min(steps, 8);
    $("busyTitle").textContent = t("steps")[Math.min(steps, 7)];
    steps++;
  }
}
function fail(message) {
  pending = null;
  $("failMsg").textContent = message;
  panes("fail");
  $("go").disabled = !file;
  restart();
}

// ---- results
let urls = [], lastReport = null;
const blob = (data, type) => { const u = URL.createObjectURL(new Blob([data], { type })); urls.push(u); return u; };
function setResult(on) {
  $("tabs").hidden = !on;
  if (!on) { $("notes").hidden = true; lastReport = null; urls.forEach(URL.revokeObjectURL); urls = []; }
}
function finish({ report, files }) {
  pending = null;
  const stem = file.name.replace(/\.[^.]+$/, "");
  $("view").src = blob(files.viewer, "text/html");
  $("sheetImg").src = blob(files.sheets, "image/png");
  $("sheetImg").alt = `${stem} DXF`;
  $("report").innerHTML = markdown(files.report);
  const zip = $("zip");
  zip.href = blob(files.zip, "application/zip");
  zip.download = `${stem}_wood.zip`;
  const box = $("dxfs");
  box.textContent = "";
  for (const [name, data] of Object.entries(files.dxf)) {
    const a = document.createElement("a");
    a.className = "button";
    a.href = blob(data, "application/dxf");
    a.download = `${stem}_${name}`;
    a.textContent = name.replace("sheet_", "DXF ").replace(".dxf", "");
    box.append(a);
  }
  lastReport = report;
  showNotes(report);
  setResult(true);
  tab("view");
  $("go").disabled = false;
  restart();      // the next run starts with clean memory
}
function showNotes(r) {
  const items = [...r.warnings.map((w) => pick(w))];
  if (form.up_axis.value === "auto" && r.up) items.push(t("upIs").replace("{up}", r.up));
  const ul = document.createElement("ul");
  items.forEach((s) => { const li = document.createElement("li"); li.textContent = s; ul.append(li); });
  $("notes").replaceChildren(ul);
  $("notes").hidden = !items.length;
}
// Python messages are "中文。/ 日本語": show the side that matches the page.
const pick = (s) => { const i = s.lastIndexOf("/ "); return i < 0 ? s : (lang === "ja" ? s.slice(i + 2) : s.slice(0, i).trim()); };
function tab(name) {
  document.querySelectorAll("[role=tab]").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === name));
  panes(name);
}

function markdown(md) {
  const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const out = [];
  const lines = md.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const l = esc(lines[i]);
    if (l.startsWith("# ")) out.push(`<h2>${l.slice(2)}</h2>`);
    else if (l.startsWith("## ")) out.push(`<h3>${l.slice(3)}</h3>`);
    else if (l.startsWith("- ")) {
      const li = [];
      for (; i < lines.length && lines[i].startsWith("- "); i++) li.push(`<li>${esc(lines[i].slice(2))}</li>`);
      i--;
      out.push(`<ul>${li.join("")}</ul>`);
    } else if (l.startsWith("|")) {
      const rows = [];
      for (; i < lines.length && lines[i].startsWith("|"); i++) rows.push(esc(lines[i]).split("|").slice(1, -1).map((c) => c.trim()));
      i--;
      const [head, , ...body] = rows;
      out.push(`<div class="wrap"><table><thead><tr>${head.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
    } else if (l.trim()) out.push(`<p>${l}</p>`);
  }
  return out.join("");
}

// ---- input
function take(f) {
  if (!f) return;
  if (!FORMATS.test(f.name)) { $("failMsg").textContent = t("notMesh"); setResult(false); panes("fail"); return; }
  file = f;
  $("dropTitle").textContent = f.name;
  $("dropSub").textContent = `${(f.size / 1e6).toFixed(1)} MB`;
  $("go").disabled = false;
  run();
}
$("file").addEventListener("click", (e) => { e.target.value = ""; });   // choosing the same file again still fires change
$("file").addEventListener("change", (e) => take(e.target.files[0]));
let depth = 0;
addEventListener("dragenter", (e) => { e.preventDefault(); depth++; document.body.classList.add("dragging"); });
addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; document.body.classList.remove("dragging"); } });
addEventListener("dragover", (e) => e.preventDefault());
addEventListener("drop", (e) => { e.preventDefault(); depth = 0; document.body.classList.remove("dragging"); if (!pending) take(e.dataTransfer.files[0]); });

form.addEventListener("input", syncSliders);
form.addEventListener("submit", (e) => { e.preventDefault(); if (!pending) run(); });
$("reset").addEventListener("click", () => { store.drop(STORE); fill(defaults); });
$("cancel").addEventListener("click", () => { pending = null; restart(); panes(lastReport ? "view" : "empty"); $("go").disabled = !file; if (!lastReport) setResult(false); });
document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => tab(b.dataset.tab)));
document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => { lang = b.dataset.lang; store.set("mesh2wood.lang", lang); applyLang(); }));

(async () => {
  defaults = await (await fetch("settings.json", { cache: "no-cache" })).json().catch(() => null);
  if (defaults) fill({ ...defaults, ...store.get(STORE) });
  applyLang();
  startWorker();
})();
