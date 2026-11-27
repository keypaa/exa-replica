"""Local web labeling tool (stdlib only, zero-install). Gate 3 κ calibration.

Run:  python3 bench/rtx/label_tool.py
Then open http://127.0.0.1:8765 — read each (query, text), click 0-3 (or press
0/1/2/3). Progress is saved to bench/results/human_labels.jsonl after each label.
When done: python3 bench/rtx/kappa_label.py score
"""

from __future__ import annotations

import errno
import http.server
import json
import os
import subprocess
from pathlib import Path

PATH = Path("bench/results/human_labels.jsonl")
# D14: allow an alternate port for verification / avoiding a stale server.
PORT = int(os.environ.get("LABEL_TOOL_PORT", "8765"))

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Sift labeler</title>
<style>
body{font-family:system-ui,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#111}
#progress{color:#666;font-size:14px;margin-bottom:12px}
.card{border:1px solid #ddd;border-radius:10px;padding:18px}
h3{margin:0 0 6px}.obj{color:#555;font-size:14px;margin:0 0 12px}
pre{white-space:pre-wrap;word-wrap:break-word;background:#f7f7f7;padding:12px;border-radius:8px;max-height:340px;overflow:auto;font-size:15px}
.btns{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
button{font-size:15px;padding:12px 16px;border-radius:8px;border:1px solid #bbb;background:#fff;cursor:pointer}
button:hover{background:#eef}
.done{text-align:center;padding:60px 0;font-size:20px}
</style></head><body>
<div id="app"><div id="progress"></div>
<div class="card"><h3 id="query"></h3><p class="obj" id="objective"></p><pre id="text"></pre>
<div class="btns">
<button data-l="0">0 · Irrelevant</button>
<button data-l="1">1 · Somewhat</button>
<button data-l="2">2 · Relevant</button>
<button data-l="3">3 · Highly relevant</button>
</div></div></div>
<script>
let cur=null;
async function load(){
  const r=await fetch('/api/row').then(r=>r.json());
  if(r.done){document.getElementById('app').innerHTML='<div class="done">Done — all labeled.<br>Run: python3 bench/rtx/kappa_label.py score</div>';return;}
  cur=r;
  document.getElementById('query').textContent=r.query;
  document.getElementById('objective').textContent=r.objective?('Objective: '+r.objective):'(no objective)';
  document.getElementById('text').textContent=r.text;
  document.getElementById('progress').textContent=(r.labeled)+' / '+r.total+' labeled';
}
async function label(l){
  await fetch('/api/label',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({index:cur.index,label:l})});
  load();
}
document.querySelectorAll('button[data-l]').forEach(b=>b.onclick=()=>label(parseInt(b.dataset.l)));
document.addEventListener('keydown',e=>{if(['0','1','2','3'].includes(e.key))label(parseInt(e.key));});
load();
</script></body></html>"""


def _load() -> list[dict]:
    return [json.loads(line) for line in PATH.read_text().splitlines() if line.strip()]


def _save(rows: list[dict]) -> None:
    PATH.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        rows = _load()
        if self.path == "/":
            b = HTML.encode()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif self.path == "/api/row":
            idx = next((i for i, r in enumerate(rows) if r.get("human_label") is None), None)
            labeled = sum(1 for x in rows if x.get("human_label") is not None)
            if idx is None:
                self._json({"done": True, "labeled": labeled, "total": len(rows)})
            else:
                r = rows[idx]
                self._json(
                    {
                        "index": idx,
                        "query": r["query"],
                        "objective": r.get("objective", ""),
                        "text": r["text"],
                        # D14: 'done' is a boolean flag only; 'labeled' is the count.
                        # Overloading 'done' with a count made 1 label look like
                        # completion in the browser (if(r.done)).
                        "done": False,
                        "labeled": labeled,
                        "total": len(rows),
                    }
                )
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/label":
            n = int(self.headers.get("content-length", 0))
            data = json.loads(self.rfile.read(n))
            rows = _load()
            rows[data["index"]]["human_label"] = data["label"]
            _save(rows)
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)


def _port_holder(port: int) -> str:
    """Best-effort: report the process already listening on ``port``."""
    try:
        out = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, timeout=2, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    for line in out.splitlines():
        if "LISTEN" in line and f":{port} " in line:
            return line.strip()
    return ""


def main() -> None:
    if not PATH.exists():
        raise SystemExit("run: python3 bench/rtx/kappa_label.py prepare --n 100 first")
    rows = _load()
    labeled = sum(1 for r in rows if r.get("human_label") is not None)
    print(
        f"loaded {len(rows)} rows from {PATH}: "
        f"{labeled} labeled, {len(rows) - labeled} remaining",
        flush=True,
    )
    try:
        srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        holder = _port_holder(PORT)
        hint = f"\n  holder: {holder}" if holder else ""
        raise SystemExit(
            f"port {PORT} is busy — a stale label_tool.py is probably still running.{hint}\n"
            f"Kill it: `ss -ltnp | grep {PORT}` then `kill <pid>`, and retry.\n"
            f"Or use a free port: LABEL_TOOL_PORT=<port> python3 bench/rtx/label_tool.py"
        ) from None
    print(f"labeling tool: http://127.0.0.1:{PORT}  (Ctrl-C to stop)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()