#!/bin/bash
# export_light.sh : build the LIGHT variant (params_light.json: each wing as drawn, no cup, the robe up to the outline), reduce it to ~16000 triangles
# (decimate.py) and write light.obj (the light proxy source for remake/tools/furniture_ops.py); the remake parameters are restored afterwards
cd /home/deck/lktest/sculpt || exit 1
cp params.json params_remake.json; cp params_light.json params.json
NOREND=1 ./all.sh "" | tail -1; cp angel_s.obj angel_light_full.obj
cp params_remake.json params.json
DC_IN=$PWD/angel_light_full.obj DC_OUT=$PWD/light_raw.obj DC_TRIS=${1:-16000} flatpak run --filesystem=home org.blender.Blender -b --python $PWD/decimate.py 2>&1 | grep decimated
python3 - <<'PY'
out = ["# light proxy: church angel statue, SCULPT light variant (remake/recipes/church_angel_sculpt, params_light.json, export_light.sh). GAME coordinates x east, y south, z up, world units.\n",
       "# our own geometry (measured rings / drawn outline of the statue, modelled parts); read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n"]
for l in open('light_raw.obj'):
    if l.startswith('v '):
        x, y, z = map(float, l.split()[1:4]); out.append('v %.3f %.3f %.3f\n' % (x, y, max(32.0, z)))   # nothing below the pedestal top
    elif l.startswith('f '): out.append(l)
open('light.obj', 'w').write(''.join(out))
PY
python3 chk.py light.obj | head -1
