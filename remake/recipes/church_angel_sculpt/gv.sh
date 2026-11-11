#!/bin/bash
# gv.sh TAG [OBJ] : exact game view of the sculpt beside the original sprite (same window, same scale)
cd /home/deck/lktest/sculpt || exit 1
GV_OBJ=$PWD/${2:-angel_s}.obj GV_OUT=$PWD/gv_r.png flatpak run --filesystem=home org.blender.Blender -b --python $PWD/gameview.py > gv.log 2>&1
ffmpeg -loglevel error -y -i ref/full.png -vf "crop=64:66:10:44,scale=iw*14:ih*14:flags=neighbor" gv_s.png
ffmpeg -loglevel error -y -i gv_s.png -i gv_r.png -filter_complex "[0][1]blend=all_expr='A*0.5+B*0.5'[m];[0][1][m]hstack=inputs=3" gv_$1.png; echo gv $(grep -c 'gv done' gv.log)
