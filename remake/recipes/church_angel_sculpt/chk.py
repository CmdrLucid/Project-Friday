import json, sys
exec(open('/home/deck/Project-Friday-Test/lktest/pult2/chk.py').read().split('def check_mesh')[0])
mask = {tuple(p) for p in json.load(open('/home/deck/Project-Friday-Test/lktest/angel3/mask.json'))}; U0, V0 = 1064, 280
def load(fn):
    V, Fc = [], []
    for l in open(fn):
        if l.startswith('v '): V.append(tuple(map(float, l.split()[1:4])))
        elif l.startswith('f '): Fc.append([int(t) - 1 for t in l.split()[1:]])
    return V, Fc
def proj(p): return (p[0]-p[1]+1184, (p[0]+p[1])/2-p[2])
def cov(V, Fc):
    out = set()
    for f in Fc:
        pts = [proj(V[i]) for i in f]
        for t in range(1, len(pts) - 1):
            A_, B_, C_ = pts[0], pts[t], pts[t+1]
            e = lambda P1, P2, x, y: (P2[0]-P1[0])*(y-P1[1])-(P2[1]-P1[1])*(x-P1[0]); ar = e(A_, B_, C_[0], C_[1])
            if abs(ar) < 1e-9: continue
            for vv in range(int(min(A_[1],B_[1],C_[1])), int(max(A_[1],B_[1],C_[1]))+1):
                for uu in range(int(min(A_[0],B_[0],C_[0])), int(max(A_[0],B_[0],C_[0]))+1):
                    x, y = uu+.5, vv+.5
                    if e(B_,C_,x,y)/ar >= -1e-6 and e(C_,A_,x,y)/ar >= -1e-6 and e(A_,B_,x,y)/ar >= -1e-6: out.add((uu-U0, vv-V0))
    return out
if __name__ == '__main__':
    fns = sys.argv[1:]; c = set()
    for fn in fns: c |= cov(*load(fn))
    print('drawn', len(mask), 'cov', len(c), 'outside', len(c - mask), 'missed', len(mask - c), 'IoU %.3f' % (len(c & mask) / len(c | mask)))
    if '-v' in sys.argv or True:
        for v in range(46, 106): print('%3d ' % v + ''.join(('#' if (u, v) in mask else 'O') if (u, v) in c else ('m' if (u, v) in mask else '.') for u in range(14, 72)))
