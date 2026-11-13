#!/bin/bash
cd /home/deck/lktest/sculpt || exit 1
R_OUT=$PWD R_OBJ=$PWD/${1:-angel_s}.obj R_SCALE=60 R_PRE=sc flatpak run --filesystem=home org.blender.Blender -b --python /home/deck/lktest/pult2/clay.py > r.log 2>&1
ffmpeg -loglevel error -y -i sc_0.png -i sc_1.png -i sc_2.png -i sc_3.png -filter_complex "hstack=inputs=4,scale=1800:-1" sc_all.png; echo rendered $(grep -c Saved r.log)
