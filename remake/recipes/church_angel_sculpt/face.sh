#!/bin/bash
# face.sh : close-ups of the head (front, 3/4 left, 3/4 right, side, game view)
cd /home/deck/lktest/sculpt || exit 1
python3 - <<'PY'
V=[];F=[]
for l in open('/home/deck/lktest/sculpt/angel_s.obj'):
    if l.startswith('v '): V.append(tuple(map(float,l.split()[1:4])))
    elif l.startswith('f '): F.append([int(t)-1 for t in l.split()[1:]])
keep=[f for f in F if all(V[i][2]>=32+33.5 and abs((V[i][0]-375.75)-(V[i][1]-449.25))<8.5 and (V[i][0]-375.75)+(V[i][1]-449.25)>-5 for i in f)]
used=sorted({i for f in keep for i in f}); m={o:n for n,o in enumerate(used)}
open('/home/deck/lktest/sculpt/fc.obj','w').write(''.join('v %.4f %.4f %.4f\n'%V[i] for i in used)+''.join('f '+' '.join(str(m[i]+1) for i in f)+'\n' for f in keep))
PY
R_SUNYAW=${SY:-20} R_OUT=$PWD R_OBJ=$PWD/fc.obj R_SCALE=${S:-12} R_PRE=fc R_VIEWS="0:5,-35:8,35:8,90:5,0:35.26" flatpak run --filesystem=home org.blender.Blender -b --python $PWD/clay2.py > r8.log 2>&1
ffmpeg -loglevel error -y -i fc_0.png -i fc_1.png -i fc_2.png -i fc_3.png -i fc_4.png -filter_complex "hstack=inputs=5,scale=1800:-1" fc_all.png; echo face $(grep -c Saved r8.log)
