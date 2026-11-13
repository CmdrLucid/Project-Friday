#!/bin/bash
# arm.sh : close-ups of the arms + scroll: front, front from above, both sides, game view
cd /home/deck/lktest/sculpt || exit 1
python3 - <<'PY'
V=[];F=[]
for l in open('/home/deck/lktest/sculpt/angel_s.obj'):
    if l.startswith('v '): V.append(tuple(map(float,l.split()[1:4])))
    elif l.startswith('f '): F.append([int(t)-1 for t in l.split()[1:]])
keep=[f for f in F if all(32+24<=V[i][2]<=32+38 and V[i][0]>372.5 for i in f)]
used=sorted({i for f in keep for i in f}); m={o:n for n,o in enumerate(used)}
open('/home/deck/lktest/sculpt/arm.obj','w').write(''.join('v %.4f %.4f %.4f\n'%V[i] for i in used)+''.join('f '+' '.join(str(m[i]+1) for i in f)+'\n' for f in keep))
PY
R_SUNYAW=${SY:-30} R_OUT=$PWD R_OBJ=$PWD/arm.obj R_SCALE=${S:-19} R_PRE=arm R_VIEWS="45:5,45:40,0:15,90:15,0:30" flatpak run --filesystem=home org.blender.Blender -b --python $PWD/clay2.py > r14.log 2>&1
ffmpeg -loglevel error -y -i arm_0.png -i arm_1.png -i arm_2.png -i arm_3.png -i arm_4.png -filter_complex "hstack=inputs=5,scale=2000:-1" arm_all.png; echo arm $(grep -c Saved r14.log)
