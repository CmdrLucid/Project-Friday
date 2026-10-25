#!/usr/bin/env python3
"""Builds the remake's local assets: kiln recipes (tools/remake/models.kx.js) -> GLB -> .r3m models in ~/.landstalker_remake/models/ (never in git).
Needs the toolchain of INDEX 'remake toolchain' (Node + kiln in ~/remake_tools).  usage: python3 tools/remake_assets.py"""
import os, subprocess, sys, glob, shutil
here = os.path.dirname(os.path.abspath(__file__)); home = os.path.expanduser("~")
node = os.path.join(home, "remake_tools/node/bin"); kiln = os.path.join(home, "remake_tools/kiln/bin/kiln.js")
out = os.path.join(home, ".landstalker_remake"); work = os.path.join(out, "build"); mdl = os.path.join(out, "models")
os.makedirs(work, exist_ok=True); os.makedirs(mdl, exist_ok=True)
env = dict(os.environ); env["PATH"] = node + os.pathsep + env["PATH"]
shutil.copy(os.path.join(here, "remake/models.kx.js"), os.path.join(work, "models.kx.js"))
r = subprocess.run(["node", kiln, "build", "models.kx.js"], cwd=work, env=env, capture_output=True, text=True)
print(r.stdout[-600:]); 
if r.returncode: print(r.stderr[-600:]); sys.exit(1)
for g in sorted(glob.glob(os.path.join(work, "out/models/*.glb"))):
    name = os.path.splitext(os.path.basename(g))[0]
    subprocess.run([sys.executable, os.path.join(here, "remake/glb2r3m.py"), g, os.path.join(mdl, name + ".r3m")], check=True)
print("models in", mdl)
