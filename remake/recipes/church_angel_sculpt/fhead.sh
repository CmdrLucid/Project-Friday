#!/bin/bash
# fhead.sh TAG : head only (no hair), big close-ups of the lower face: front, 3/4, side, from below
cd /home/deck/Project-Friday-Test/lktest/sculpt || exit 1
python3 head.py headm.obj hairm.obj >/dev/null || exit 1
R_SUNYAW=${SY:-20} R_OUT=$PWD R_OBJ=$PWD/headm.obj R_SCALE=${S:-7.5} R_PRE=fh R_VIEWS="0:0,-40:5,90:0,-20:-20" flatpak run --filesystem=home org.blender.Blender -b --python $PWD/clay2.py > r9.log 2>&1
ffmpeg -loglevel error -y -i fh_0.png -i fh_1.png -i fh_2.png -i fh_3.png -filter_complex "hstack=inputs=4,scale=2000:-1" fh_$1.png; echo head $(grep -c Saved r9.log)
