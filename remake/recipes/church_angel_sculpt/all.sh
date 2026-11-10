#!/bin/bash
# all.sh PARAMS : body + wings + post + merge + check + render
cd /home/deck/lktest/sculpt || exit 1
./run.sh "$1" >/dev/null && python3 wing.py wing.obj >/dev/null && python3 post.py raw.obj body_s.obj 0.7 >/dev/null
python3 - <<'PY'
V=[];Fs=[]
for fn in ('/home/deck/lktest/sculpt/body_s.obj','/home/deck/lktest/sculpt/wing.obj'):
    o=len(V)
    for l in open(fn):
        if l.startswith('v '): V.append(l)
        elif l.startswith('f '): Fs.append('f '+' '.join(str(int(t)+o) for t in l.split()[1:])+'\n')
open('/home/deck/lktest/sculpt/angel_s.obj','w').write(''.join(V)+''.join(Fs))
PY
python3 chk.py body_s.obj wing.obj | head -1; [ -z "$NOREND" ] && ./rend.sh
