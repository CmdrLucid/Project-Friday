#!/bin/bash
# hh.sh TAG : head + hair only (before post.py): front, 3/4, side, back, top
cd /home/deck/Project-Friday-Test/lktest/sculpt || exit 1
python3 head.py headm.obj hairm.obj >/dev/null || exit 1
python3 - <<'PY'
V=[];Fs=[]
for fn in ('headm.obj','hairm.obj'):
    o=len(V)
    for l in open(fn):
        if l.startswith('v '): V.append(l)
        elif l.startswith('f '): Fs.append('f '+' '.join(str(int(t)+o) for t in l.split()[1:])+'\n')
open('hh.obj','w').write(''.join(V)+''.join(Fs))
PY
R_SUNYAW=${SY:-20} R_OUT=$PWD R_OBJ=$PWD/hh.obj R_SCALE=${S:-13} R_PRE=hh R_VIEWS="0:5,-40:10,90:5,180:10,0:60" flatpak run --filesystem=home org.blender.Blender -b --python $PWD/clay2.py > r12.log 2>&1
ffmpeg -loglevel error -y -i hh_0.png -i hh_1.png -i hh_2.png -i hh_3.png -i hh_4.png -filter_complex "hstack=inputs=5,scale=2000:-1" hh_$1.png; echo hh $(grep -c Saved r12.log)
