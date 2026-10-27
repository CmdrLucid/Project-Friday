#!/usr/bin/env python3
"""editor.py [ROOM]  -- the remake's small map editor (user 2026-10-27: 'kleiner simpler Mapeditor ... Sprites platzieren, 3D-Assets, Gelaende').

Starts a local web server (http://localhost:8765, only reachable from this machine) and opens the page remake/editor/index.html in the browser.
The page shows the original picture of the room and the remake render (fade slider), every pixel card (pines, bushes, statue) as a marker; cards are
moved / deleted / added there and saved to remake/rooms/<room>.json (the overrides that recipes/room_c.py applies after its automatic placement).
'Rendern' runs the room render in Blender (same command as by hand) and reloads the picture.
Local data (never in git): ~/.landstalker_remake/rooms/<room>_room_c (original picture), assets/room_c (render + cards.json), props (card images)."""
import json, os, subprocess, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOM = int(sys.argv[1]) if len(sys.argv) > 1 else 592
PORT = int(os.environ.get("EDITOR_PORT", "8765"))
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PAGE = os.path.join(REPO, "remake", "editor")
OVR = os.path.join(REPO, "remake", "rooms", "%d.json" % ROOM)
LOCAL = os.path.expanduser("~/.landstalker_remake")
ORIG = os.path.join(LOCAL, "rooms", "%d_room_c" % ROOM, "full.png")
OUT = os.path.join(LOCAL, "assets", "room_c")
PROPS = os.path.join(LOCAL, "props")
FIGURE = os.path.join(LOCAL, "figures", "nigel_a4.png")
render = dict(state="idle", started=0.0, took=0.0, log="")


DRAFT = os.path.join(LOCAL, "tmp", "editor_draft_%d.json" % ROOM)


def clean(d):
    return dict(move={k: [round(float(v), 2) for v in m] for k, m in d.get("move", {}).items() if any(abs(float(v)) > 1e-3 for v in m)},
                delete=sorted(set(d.get("delete", []))),
                add=[dict(kind=str(a["kind"]), x=round(float(a["x"]), 2), y=round(float(a["y"]), 2), z=round(float(a["z"]), 2)) for a in d.get("add", [])])


def run_render():
    render.update(state="running", started=time.time(), log="")
    env = dict(os.environ, R_PX="2", R_ROOM=str(ROOM), R_EDITS_FILE=DRAFT)     # renders the page's current (maybe unsaved) edits; the room file stays untouched
    if os.path.exists(FIGURE): env["R_FIGURE"] = FIGURE
    print("render started ...", flush=True)
    p = subprocess.run([sys.executable, os.path.join(REPO, "remake", "tools", "build_asset.py"), "room_c"], cwd=REPO, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = [l for l in p.stdout.splitlines() if l.startswith(("editor", "sort_cards", "pixel plants", "Traceback", "Error")) or "Error" in l]
    render.update(state="done" if p.returncode == 0 and os.path.exists(os.path.join(OUT, "cards.json")) else "failed",
                  took=time.time() - render["started"], log="\n".join(lines[-30:] if p.returncode == 0 else p.stdout.splitlines()[-40:]))
    print("render %s after %.0f s" % (render["state"], render["took"]), flush=True)


class H(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

    def file(self, path, ctype):
        if not os.path.isfile(path): return self.send(404, "not found: " + path, "text/plain")
        self.send(200, open(path, "rb").read(), ctype)

    def do_GET(self):
        u = self.path.split("?")[0]
        if u in ("/", "/index.html"): return self.file(os.path.join(PAGE, "index.html"), "text/html; charset=utf-8")
        if u == "/editor.js": return self.file(os.path.join(PAGE, "editor.js"), "text/javascript")
        if u == "/img/original.png": return self.file(ORIG, "image/png")
        if u == "/img/render.png": return self.file(os.path.join(OUT, "game.png"), "image/png")
        if u.startswith("/img/") and u.endswith(".png") and "/" not in u[5:]: return self.file(os.path.join(OUT, u[5:]), "image/png")   # renders of every view
        if u.startswith("/props/"):                                              # card images: only files inside the props folder
            p = os.path.realpath(os.path.join(PROPS, u[len("/props/"):]))
            if not p.startswith(os.path.realpath(PROPS) + os.sep): return self.send(403, "no", "text/plain")
            return self.file(p, "image/png")
        if u == "/api/room":
            cj = os.path.join(OUT, "cards.json")
            if not os.path.exists(cj): return self.send(404, json.dumps(dict(error="no cards.json yet: press Rendern once")))
            d = json.load(open(cj))
            for c in d["cards"]:                                                 # the page loads card images by name below props/
                c["img"] = os.path.relpath(c["png"], PROPS) if os.path.realpath(c["png"]).startswith(os.path.realpath(PROPS)) else None
            d["kinds"] = sorted(f[:-4] for f in os.listdir(PROPS) if f.endswith(".png"))
            d["overrides"] = json.load(open(OVR)) if os.path.exists(OVR) else {}
            d["render_time"] = os.path.getmtime(cj)
            return self.send(200, json.dumps(d))
        if u == "/api/render": return self.send(200, json.dumps(render))
        self.send(404, "not found", "text/plain")

    def do_POST(self):
        u = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length", "0")); body = self.rfile.read(n) if n else b""
        if u == "/api/save":
            c = clean(json.loads(body or b"{}"))
            os.makedirs(os.path.dirname(OVR), exist_ok=True)
            open(OVR, "w").write(json.dumps(c, indent=1, sort_keys=True) + "\n")
            print("saved", OVR, "(%d moved, %d deleted, %d added)" % (len(c["move"]), len(c["delete"]), len(c["add"])), flush=True)
            return self.send(200, json.dumps(dict(ok=True)))
        if u == "/api/render":
            if render["state"] != "running":
                os.makedirs(os.path.dirname(DRAFT), exist_ok=True)
                open(DRAFT, "w").write(json.dumps(clean(json.loads(body or b"{}"))))
                threading.Thread(target=run_render, daemon=True).start()
            return self.send(200, json.dumps(dict(ok=True)))
        self.send(404, "not found", "text/plain")


if __name__ == "__main__":
    if not os.path.exists(ORIG): sys.exit("original picture missing: %s (rom_picture.py, see remake/ASSETS.md 'Room blockout')" % ORIG)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = "http://localhost:%d/" % PORT
    print("Map-Editor laeuft: %s  (Raum %d; Beenden: Strg+C in diesem Fenster)" % (url, ROOM), flush=True)
    if not os.environ.get("EDITOR_NO_BROWSER"): threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("Editor beendet.")
