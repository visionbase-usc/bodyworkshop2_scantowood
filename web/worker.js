// Runs Python in the background so the page never freezes. One worker per calculation:
// the page starts a fresh one afterwards, because WebAssembly memory never shrinks.
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const PACKAGES = ["numpy", "scipy", "scikit-image", "shapely", "matplotlib", "micropip"];
const PYPI = ["trimesh==5.2.0", "ezdxf==1.4.5"];
const SOURCES = ["mesh2wood.py", "settings.json", "web/bridge.py", "m2w/__init__.py", "m2w/construct.py", "m2w/joinery.py",
  "m2w/output.py", "m2w/stylize.py", "m2w/voxelize.py", "m2w/viewer_template.html", "m2w/vendor/three.min.js", "m2w/vendor/OrbitControls.js"];

importScripts(PYODIDE + "pyodide.js");

const ready = (async () => {
  const py = await loadPyodide({ indexURL: PYODIDE });
  await py.loadPackage(PACKAGES, { messageCallback: () => {} });
  py.globals.set("PYPI", py.toPy(PYPI));
  await py.runPythonAsync("import micropip\nawait micropip.install(PYPI)");
  py.FS.mkdirTree("/app/m2w/vendor");
  py.FS.mkdirTree("/app/web");
  await Promise.all(SOURCES.map(async (s) => {
    const r = await fetch("../" + s, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${s}: ${r.status}`);
    py.FS.writeFile("/app/" + s, new Uint8Array(await r.arrayBuffer()));
  }));
  await py.runPythonAsync("import sys\nsys.path[:0] = ['/app', '/app/web']\nimport bridge");
  postMessage({ type: "ready" });
  return py;
})();
ready.catch((e) => postMessage({ type: "failed", message: String(e) }));

onmessage = async ({ data: { name, bytes, cfg } }) => {
  try {
    const py = await ready;
    py.FS.mkdirTree("/in");
    const path = "/in/" + name.replace(/[\\/]/g, "_");
    py.FS.writeFile(path, new Uint8Array(bytes));
    const compute = py.pyimport("bridge").compute;
    const [summary, zip] = compute(path, JSON.stringify(cfg), (line) => postMessage({ type: "log", line })).toJs();
    const result = JSON.parse(summary);
    if (result.error) return postMessage({ type: "error", message: result.error });
    const read = (f, encoding) => py.FS.readFile("/out/" + f, encoding ? { encoding } : undefined);
    const files = { zip: new Uint8Array(zip), sheets: read("sheets.png"), viewer: read("viewer.html", "utf8"), report: read("report.md", "utf8"), dxf: {} };
    for (const f of result.dxf) files.dxf[f] = read(f);
    postMessage({ type: "done", report: result.report, files });
  } catch (e) {
    const s = String(e);
    const memory = e instanceof RangeError || /memory|MemoryError/i.test(s);
    postMessage({ type: "error", message: memory ? "memory" : s.trim().split("\n").slice(-3).join("\n") });
  }
};
