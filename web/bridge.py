"""Browser entry point: the same run() as the command line, inside Pyodide."""
import io
import json
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import mesh2wood as W


def _plain(o):
    return o.tolist() if hasattr(o, "tolist") else str(o)


def compute(path, cfg_json, log):
    """Returns (summary json, zip bytes). A problem the user can fix comes back as {"error": ...}."""
    out = Path("/out")
    try:
        res = W.run(path, json.loads(cfg_json), out, log=log)
    except (ValueError, FileNotFoundError) as e:
        return json.dumps({"error": str(e)}), b""
    except MemoryError:
        return json.dumps({"error": "memory"}), b""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.iterdir()):
            z.write(f, f.name)
    return json.dumps({"report": res["report"], "dxf": [f.name for f in res["files"]]}, default=_plain), buf.getvalue()
