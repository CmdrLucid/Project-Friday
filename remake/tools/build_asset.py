#!/usr/bin/env python3
"""Builds one remake asset with Blender (headless): python3 remake/tools/build_asset.py hut   ->  ~/.landstalker_remake/assets/<name>/ (GLB + preview PNGs, local, never in git)."""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); name = sys.argv[1]
out = os.path.join(os.path.expanduser("~"), ".landstalker_remake", "assets", name); os.makedirs(out, exist_ok=True)
env = dict(os.environ); env["R_OUT"] = out
r = subprocess.run(["flatpak", "run", "--command=blender", "org.blender.Blender", "-b", "-P", os.path.join(here, "..", "recipes", name + ".py")], env=env, capture_output=True, text=True)
print((r.stdout + r.stderr)[-1500:]); sys.exit(r.returncode)
