#!/usr/bin/env python3
"""blockfind.py DIR_OF_REPLAY_DUMP_DIRS | blockfind.py --one DUMP.bin
Finds how the map block arrays in work RAM (g_ForegroundBlocks $FF7C02 = layer A, g_BackgroundBlocks $FFA6CA = layer B, word per cell, id = word & $03FF, index 148 * y + 2 * x like the height map)
appear on the VDP scroll planes of the same dump (dump layout: RAM 64K | regs 32 | CRAM 128 | VSRAM 128 | VRAM 64K, words byte-swapped like the RAM): the 2x2 tile pattern of a block (g_Blockset $FF5C02, 8 bytes per block)
is looked up in the nametable of the plane. Result (FORMATS 'Block map'): plane cell = ((x - y + k1) mod 32, ((x + y + k2) >> 1) mod 16), and the screen pixel of block (x, y) is
  x = 16 (x - y) + (cam2 - cam0 + 160) [layer A another -16],  y = 8 (x + y) - (cam0 + cam2) / 2 + 104      (cam0 = word $FF1200, cam2 = word $FF1202).
Prints the per-dump deltas between the plane fit and this prediction (0,0 = exact; (496,0) = layer A is 16 px to the left)."""
import sys, os, struct, collections
def analyse(path):
    d=open(path,'rb').read()
    ram, reg, vs, vram = d[:0x10000], d[0x10000:0x10020], d[0x100A0:0x10120], d[0x10120:0x20120]
    RB=lambda a: ram[(a&0xFFFF)^1]
    RW=lambda a: (RB(a)<<8)|RB(a+1)
    SG=lambda a: RW(a)-65536 if RW(a)&0x8000 else RW(a)
    VW=lambda a: (vram[a^1]<<8)|vram[(a+1)^1]
    SW=lambda i: (vs[2*i^1]<<8)|vs[(2*i+1)^1]
    if reg[11]&7: return None            # per-line / per-column scroll: skip
    hsb=(reg[13]&0x3F)<<10; hsA=VW(hsb); hsB=VW(hsb+2); vsA=SW(0); vsB=SW(1)
    bases={'A':(reg[2]&0x38)<<10,'B':(reg[4]&7)<<13}
    scr={'A':(hsA,vsA),'B':(hsB,vsB)}
    def blockset(i): a=0xFF5C02+8*i; return [RW(a),RW(a+2),RW(a+4),RW(a+6)]
    out=[]
    cam0,cam2=SG(0xFF1200),SG(0xFF1202)
    for pn,ln,lb in (('A','FG',0xFF7C02),('B','BG',0xFFA6CA)):
        base=bases[pn]
        idx={}
        for row in range(16):
            for col in range(32):
                q=tuple(VW(base+2*((2*row+dy)*64+2*col+dx))&0x7FF for dy in (0,1) for dx in (0,1)); idx.setdefault(q,[]).append((col,row))
        hits=[]
        for y in range(74):
            for x in range(74):
                bid=RW(lb+148*y+2*x)&0x3FF
                if not bid: continue
                bs=blockset(bid); q=tuple(t&0x7FF for t in bs)
                if q in idx and len(idx[q])==1: hits.append((x,y,idx[q][0]))
        if len(hits)<15: continue
        best=None
        h1=collections.Counter((c-(x-y))%32 for x,y,(c,r) in hits)
        k1,n1=h1.most_common(1)[0]
        h2=collections.Counter((r-((x+y)//2))%16 for x,y,(c,r) in hits)
        k2,n2=h2.most_common(1)[0]
        hs,vsv=scr[pn]
        hsv=hs if hs<32768 else hs-65536
        # block (x,y) top-left px: 16*((x-y+k1)%32)+hs  ; use unwrapped (x-y+k1)
        X0=(16*k1+hsv)%512; Y0=(16*k2-(vsv%512))%256
        # prediction from camera for block (0,0): sx = -cam0+cam2+160 ; sy = -(cam0+cam2)//2+104
        Px=(-cam0+cam2+160)%512; Py=(-(cam0+cam2)//2+104)%256
        out.append((pn,ln,len(hits),n1,n2,(X0-Px)%512,(Y0-Py)%256))
    return out
if __name__=='__main__':
    if sys.argv[1]=='--one':
        for o in (analyse(sys.argv[2]) or []): print(o)
        sys.exit(0)
    rows=[]
    for name in sorted(os.listdir(sys.argv[1])):
        if name.startswith('rp_') and not name.endswith('.srm'):
            fl=sorted(os.listdir(sys.argv[1]+'/'+name))
            for f in fl[::max(1,len(fl)//25)]:
                p='%s/%s/%s'%(sys.argv[1],name,f)
                r=analyse(p)
                if r:
                    for o in r: rows.append((name,f)+o)
    c=collections.Counter((o[7],o[8]) for o in rows if o[5]>=0.5*o[4] and o[6]>=0.5*o[4])
    print(len(rows),'plane/array fits;  delta (x,y) most common:',c.most_common(8))
    for o in rows[:12]: print(o)
