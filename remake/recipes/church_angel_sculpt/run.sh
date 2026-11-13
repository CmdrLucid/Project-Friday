#!/bin/bash
# run.sh [params-json] : parts -> Blender metaballs -> raw.obj -> projection check
cd /home/deck/lktest/sculpt || exit 1
[ -n "$1" ] && echo "$1" > params.json
python3 sculpt.py p >/dev/null && MB_IN=$PWD/parts.json MB_OUT=$PWD/raw.obj MB_RES=${RES:-0.35} flatpak run --filesystem=home org.blender.Blender -b --python $PWD/mb_blender.py > mb.log 2>&1
python3 chk.py raw.obj | head -1
