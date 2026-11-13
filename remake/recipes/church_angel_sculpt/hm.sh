#!/bin/bash
cd /home/deck/Project-Friday-Test/lktest/sculpt || exit 1
python3 head.py headm.obj >/dev/null
R_SUNYAW=${SY:-25} R_OUT=$PWD R_OBJ=$PWD/headm.obj R_SCALE=${S:-8.5} R_PRE=hm R_VIEWS="0:3,-30:6,30:6,90:3,0:35.26" flatpak run --filesystem=home org.blender.Blender -b --python $PWD/clay2.py > r9.log 2>&1
ffmpeg -loglevel error -y -i hm_0.png -i hm_1.png -i hm_2.png -i hm_3.png -i hm_4.png -filter_complex "hstack=inputs=5,scale=1800:-1" hm_all.png; echo hm $(grep -c Saved r9.log)
