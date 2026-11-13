#!/bin/bash
# up.sh : close-ups of the upper body (front low, 3/4, side, game view)
cd /home/deck/Project-Friday-Test/lktest/sculpt || exit 1
python3 - <<'PY'
V=[];F=[]
for l in open('/home/deck/Project-Friday-Test/lktest/sculpt/angel_s.obj'):
    if l.startswith('v '): V.append(tuple(map(float,l.split()[1:4])))
    elif l.startswith('f '): F.append([int(t)-1 for t in l.split()[1:]])
keep=[f for f in F if all(V[i][2]>=32+23 and (V[i][0]-375.75)+(V[i][1]-449.25)>-6 for i in f)]
used=sorted({i for f in keep for i in f}); m={o:n for n,o in enumerate(used)}
open('/home/deck/Project-Friday-Test/lktest/sculpt/up.obj','w').write(''.join('v %.4f %.4f %.4f\n'%V[i] for i in used)+''.join('f '+' '.join(str(m[i]+1) for i in f)+'\n' for f in keep))
PY
R_OUT=$PWD R_OBJ=$PWD/up.obj R_SCALE=${S:-24} R_PRE=up R_VIEWS="0:5,45:10,100:10,0:30" flatpak run --filesystem=home org.blender.Blender -b --python $PWD/clay2.py > r2.log 2>&1
ffmpeg -loglevel error -y -i up_0.png -i up_1.png -i up_2.png -i up_3.png -filter_complex "hstack=inputs=4,scale=1800:-1" up_all.png; echo up $(grep -c Saved r2.log)
