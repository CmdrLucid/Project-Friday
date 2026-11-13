# sym.py : one wing shape for BOTH sides (user 2026-11-10: mirrored, parallel to the wall, left = right): in the wing plane x = XW the right wing is the
# left one mirrored at y = yc (+ dz). Allowed area per side = the statue's pixels on that side (wing + head / body: a wing part behind the body is hidden).
# Template T (left side, plane pixels) = allowed_left AND mirror(allowed_right), kept to the wing pixels' neighbourhood; prints the fit and writes sym.json
import sys, json, math
sys.path.insert(0,'/home/deck/ProjectL/remake/lib'); import furniture as F
A=F.CHURCH_ANGEL4; AX,AY=A['axis']; XW=A['wing_x']; AU=AX-AY+1184.0; V0p=A['v0']; U0,V0=1064,280
wing={(int(math.floor(AU+du))-U0, V0p+v-V0) for du,v in A['wing']}
mask={tuple(p) for p in json.load(open('/home/deck/Project-Friday-Test/lktest/angel3/mask.json'))}
ax=AU-U0
Lw={p for p in wing if p[0]+0.5<ax}; Rw=wing-Lw
allowL={p for p in mask if p[0]+0.5<ax}; allowR={p for p in mask if p[0]+0.5>ax}
def toplane(u,v): U=U0+u+0.5; Vv=V0+v+0.5; y=XW+1184-U; z=(XW+y)/2-Vv; return y,z
def topix(y,z): U=XW-y+1184; Vv=(XW+y)/2-z; return int(math.floor(U-U0)), int(math.floor(Vv-V0))
def mir(p,yc,dz): y,z=toplane(*p); return topix(2*yc-y, z+dz)
res=[]
for yc10 in range(4380,4520,5):
  for dz in range(-8, 3):
    yc=yc10/10
    mR={mir(p,yc,-dz) for p in allowR}           # the right side's allowed area seen on the left
    T={p for p in allowL if p in mR and any((p[0]+a,p[1]+b) in Lw for a in (-1,0,1) for b in (-1,0,1))}
    covL=len(T&Lw)/len(Lw); mT={mir(p,yc,dz) for p in T}; covR=len(mT&Rw)/len(Rw)
    res.append((covL+covR, covL, covR, yc, dz, len(T)))
res.sort(reverse=True)
for r in res[:5]: print('cov L %.3f R %.3f yc %.1f dz %d T %d'%r[1:])
b=res[0]; json.dump(dict(yc=b[3], dz=b[4]), open('/home/deck/Project-Friday-Test/lktest/sculpt/sym.json','w'))
