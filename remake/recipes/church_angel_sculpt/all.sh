#!/bin/bash
# all.sh PARAMS : body + polygon head + wings + post + merge + check (+ render)
cd /home/deck/Project-Friday-Test/lktest/sculpt || exit 1
./run.sh "$1" >/dev/null && python3 wing.py wing.obj >/dev/null && python3 head.py headm.obj hairm.obj >/dev/null && python3 robe.py robem.obj >/dev/null && python3 scroll.py scroll.obj >/dev/null && python3 post.py robem.obj robe_s.obj 0.7 >/dev/null && python3 post.py raw.obj body_s.obj 0.7 >/dev/null && python3 post.py headm.obj head_s.obj 0.7 >/dev/null && cp hairm.obj hair_s.obj
python3 - <<'PY'
V=[];Fs=[]
for fn in ('/home/deck/Project-Friday-Test/lktest/sculpt/body_s.obj','/home/deck/Project-Friday-Test/lktest/sculpt/head_s.obj','/home/deck/Project-Friday-Test/lktest/sculpt/hair_s.obj','/home/deck/Project-Friday-Test/lktest/sculpt/robe_s.obj','/home/deck/Project-Friday-Test/lktest/sculpt/scroll.obj','/home/deck/Project-Friday-Test/lktest/sculpt/wing.obj'):
    o=len(V)
    for l in open(fn):
        if l.startswith('v '): V.append(l)
        elif l.startswith('f '): Fs.append('f '+' '.join(str(int(t)+o) for t in l.split()[1:])+'\n')
open('/home/deck/Project-Friday-Test/lktest/sculpt/angel_s.obj','w').write(''.join(V)+''.join(Fs))
PY
python3 chk.py body_s.obj head_s.obj hair_s.obj robe_s.obj scroll.obj wing.obj | head -1; [ -z "$NOREND" ] && ./rend.sh; true
