#!/usr/bin/env python3
"""z80dis.py -- Z80 instruction decoder + flow disassembler (2026-10-28, sound step 3: the front end of the planned Z80 recompiler, docs/SOUND_PLAN.md).
Decoder after the x / y / z / p / q scheme of the Z80 opcode table (all documented opcodes incl. CB, ED, DD / FD, DDCB / FDCB).
Module use:  d = decode(mem, pc)  ->  dict(len, text, kind, target, cycles)   kind: 'op' | 'jp' | 'jr' | 'jrc' (conditional) | 'jpc' | 'call' | 'callc' | 'ret' | 'retc' | 'djnz' | 'jpind' | 'halt' | 'rst'
CLI:         python3 z80dis.py ROM [start_hex=1F6000] [size_hex=1F80]  -> lists the reachable code from address 0 of the driver (flow walk) and the totals."""
import sys

R8 = ['b', 'c', 'd', 'e', 'h', 'l', '(hl)', 'a']
R16 = ['bc', 'de', 'hl', 'sp']
R16AF = ['bc', 'de', 'hl', 'af']
CC = ['nz', 'z', 'nc', 'c', 'po', 'pe', 'p', 'm']
ALU = ['add a,', 'adc a,', 'sub ', 'sbc a,', 'and ', 'xor ', 'or ', 'cp ']
ROT = ['rlc', 'rrc', 'rl', 'rr', 'sla', 'sra', 'sll', 'srl']
IM = ['0', '0', '1', '2', '0', '0', '1', '2']

def s8(b): return b - 256 if b > 127 else b

def decode(m, pc):
    """m: indexable bytes (addresses are 16 bit); returns dict"""
    def b(i): return m[(pc + i) & 0xFFFF]
    def w(i): return b(i) | (b(i + 1) << 8)
    pre = None; i = 0
    op = b(0)
    if op in (0xDD, 0xFD):
        pre = 'ix' if op == 0xDD else 'iy'; i = 1; op = b(1)
        if op in (0xDD, 0xFD, 0xED):   # prefix chain: treat the first prefix as a NOP-like 4 cycle byte
            return dict(len=1, text='nop ; prefix', kind='op', target=None, cycles=4)
    def reg(r):   # 8 bit operand name honouring DD / FD (hl -> ix / iy, (hl) -> (ix+d))
        if pre and r == 6: return None
        if pre and r in (4, 5): return pre + ('h' if r == 4 else 'l')
        return R8[r]
    d = dict(kind='op', target=None)
    x, y, z = op >> 6, (op >> 3) & 7, op & 7; p, q = y >> 1, y & 1
    HL = pre or 'hl'
    disp = None
    def idx():   # (ix+d) operand: consumes the displacement byte at i + 1
        nonlocal disp
        disp = s8(b(i + 1)); return '(%s%+d)' % (pre, disp)
    if op == 0xED and not pre:
        op2 = b(1); x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7; p, q = y >> 1, y & 1
        if x == 1:
            if z == 0: t = 'in %s,(c)' % (R8[y] if y != 6 else 'f'); n = 2; cyc = 12
            elif z == 1: t = 'out (c),%s' % (R8[y] if y != 6 else '0'); n = 2; cyc = 12
            elif z == 2: t = ('sbc hl,%s' if q == 0 else 'adc hl,%s') % R16[p]; n = 2; cyc = 15
            elif z == 3:
                a = w(2); t = ('ld (%04Xh),%s' if q == 0 else 'ld %s,(%04Xh)'); t = t % ((a, R16[p]) if q == 0 else (R16[p], a)); n = 4; cyc = 20
            elif z == 4: t = 'neg'; n = 2; cyc = 8
            elif z == 5: t = 'retn' if y != 1 else 'reti'; n = 2; cyc = 14; return dict(len=n, text=t, kind='ret', target=None, cycles=cyc)
            elif z == 6: t = 'im %s' % IM[y]; n = 2; cyc = 8
            else: t = ['ld i,a', 'ld r,a', 'ld a,i', 'ld a,r', 'rrd', 'rld', 'nop', 'nop'][y]; n = 2; cyc = 9 if y < 4 else 18
            return dict(len=n, text=t, kind='op', target=None, cycles=cyc)
        if x == 2 and z <= 3 and y >= 4:
            t = ['ldi', 'cpi', 'ini', 'outi', 'ldd', 'cpd', 'ind', 'outd', 'ldir', 'cpir', 'inir', 'otir', 'lddr', 'cpdr', 'indr', 'otdr'][(y - 4) * 4 + z]
            return dict(len=2, text=t, kind='op', target=None, cycles=16, rep=(y >= 6))
        return dict(len=2, text='nop ; ed %02X' % op2, kind='op', target=None, cycles=8)
    if op == 0xCB and not pre:
        op2 = b(1); x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
        t = ['%s %s' % (ROT[y], R8[z]), 'bit %d,%s' % (y, R8[z]), 'res %d,%s' % (y, R8[z]), 'set %d,%s' % (y, R8[z])][x]
        cyc = 8 if z != 6 else (12 if x == 1 else 15)
        return dict(len=2, text=t, kind='op', target=None, cycles=cyc)
    if pre and op == 0xCB:   # DDCB d op
        disp = s8(b(2)); op2 = b(3); x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
        a = '(%s%+d)' % (pre, disp)
        t = ['%s %s' % (ROT[y], a), 'bit %d,%s' % (y, a), 'res %d,%s' % (y, a), 'set %d,%s' % (y, a)][x]
        if z != 6 and x != 1: t += ',' + R8[z]
        return dict(len=4, text=t, kind='op', target=None, cycles=20 if x != 1 else 16)
    base = 1 if pre else 0   # operand bytes start at pc + base + 1
    def n8(): return b(base + 1)
    def n16(): return w(base + 1)
    plen = i + 1 if pre else 1
    cyc = 4
    if x == 0:
        if z == 0:
            if y == 0: return dict(len=1, text='nop', kind='op', target=None, cycles=4)
            if y == 1: return dict(len=1, text="ex af,af'", kind='op', target=None, cycles=4)
            e = s8(b(1)); tgt = (pc + 2 + e) & 0xFFFF
            if y == 2: return dict(len=2, text='djnz %04Xh' % tgt, kind='djnz', target=tgt, cycles=13)
            if y == 3: return dict(len=2, text='jr %04Xh' % tgt, kind='jr', target=tgt, cycles=12)
            return dict(len=2, text='jr %s,%04Xh' % (CC[y - 4], tgt), kind='jrc', target=tgt, cycles=12, cc=CC[y - 4])
        if z == 1:
            if q == 0:
                rr = HL if p == 2 else R16[p]
                return dict(len=plen + 2, text='ld %s,%04Xh' % (rr, n16()), kind='op', target=None, cycles=10 if not pre else 14)
            rr = HL if p == 2 else R16[p]
            return dict(len=plen, text='add %s,%s' % (HL, rr), kind='op', target=None, cycles=11 if not pre else 15)
        if z == 2:
            if p == 0 or p == 1:
                return dict(len=1, text=('ld (%s),a' if q == 0 else 'ld a,(%s)') % R16[p], kind='op', target=None, cycles=7)
            a = n16(); ln = plen + 2
            if p == 2: return dict(len=ln, text=('ld (%04Xh),%s' if q == 0 else 'ld %s,(%04Xh)') % ((a, HL) if q == 0 else (HL, a)), kind='op', target=None, cycles=16 if not pre else 20)
            return dict(len=ln, text=('ld (%04Xh),a' if q == 0 else 'ld a,(%04Xh)') % a, kind='op', target=None, cycles=13)
        if z == 3:
            rr = HL if p == 2 else R16[p]
            return dict(len=plen, text=('inc %s' if q == 0 else 'dec %s') % rr, kind='op', target=None, cycles=6 if not pre else 10)
        if z in (4, 5):
            nm = 'inc' if z == 4 else 'dec'
            if y == 6 and pre: t = '%s %s' % (nm, idx()); return dict(len=3, text=t, kind='op', target=None, cycles=23)
            return dict(len=plen, text='%s %s' % (nm, reg(y) if not (pre and y == 6) else '(hl)'), kind='op', target=None, cycles=4 if y != 6 else 11)
        if z == 6:
            if y == 6 and pre: t = 'ld %s,%02Xh' % (idx(), b(3)); return dict(len=4, text=t, kind='op', target=None, cycles=19)
            return dict(len=plen + 1, text='ld %s,%02Xh' % (reg(y), n8()), kind='op', target=None, cycles=7 if y != 6 else 10)
        return dict(len=plen, text=['rlca', 'rrca', 'rla', 'rra', 'daa', 'cpl', 'scf', 'ccf'][y], kind='op', target=None, cycles=4)
    if x == 1:
        if z == 6 and y == 6: return dict(len=plen, text='halt', kind='halt', target=None, cycles=4)
        if pre and (y == 6 or z == 6):
            a = idx()
            if y == 6: t = 'ld %s,%s' % (a, R8[z])
            else: t = 'ld %s,%s' % (R8[y], a)
            return dict(len=3, text=t, kind='op', target=None, cycles=19)
        return dict(len=plen, text='ld %s,%s' % (reg(y), reg(z)), kind='op', target=None, cycles=4 if (y != 6 and z != 6) else 7)
    if x == 2:
        if pre and z == 6: t = '%s%s' % (ALU[y], idx()); return dict(len=3, text=t, kind='op', target=None, cycles=19)
        return dict(len=plen, text='%s%s' % (ALU[y], reg(z)), kind='op', target=None, cycles=4 if z != 6 else 7)
    # x == 3
    if z == 0: return dict(len=plen, text='ret %s' % CC[y], kind='retc', target=None, cycles=11, cc=CC[y])
    if z == 1:
        if q == 0: return dict(len=plen, text='pop %s' % (HL if p == 2 else R16AF[p]), kind='op', target=None, cycles=10 if not pre else 14)
        if p == 0: return dict(len=1, text='ret', kind='ret', target=None, cycles=10)
        if p == 1: return dict(len=1, text='exx', kind='op', target=None, cycles=4)
        if p == 2: return dict(len=plen, text='jp (%s)' % HL, kind='jpind', target=None, cycles=4)
        return dict(len=plen, text='ld sp,%s' % HL, kind='op', target=None, cycles=6)
    if z == 2:
        a = w(base + 1) if False else (b(1) | (b(2) << 8))
        return dict(len=3, text='jp %s,%04Xh' % (CC[y], a), kind='jpc', target=a, cycles=10, cc=CC[y])
    if z == 3:
        if y == 0: a = b(1) | (b(2) << 8); return dict(len=3, text='jp %04Xh' % a, kind='jp', target=a, cycles=10)
        if y == 2: return dict(len=2, text='out (%02Xh),a' % b(1), kind='op', target=None, cycles=11)
        if y == 3: return dict(len=2, text='in a,(%02Xh)' % b(1), kind='op', target=None, cycles=11)
        if y == 4: return dict(len=plen, text='ex (sp),%s' % HL, kind='op', target=None, cycles=19)
        if y == 5: return dict(len=1, text='ex de,hl', kind='op', target=None, cycles=4)
        if y == 6: return dict(len=1, text='di', kind='op', target=None, cycles=4)
        if y == 7: return dict(len=1, text='ei', kind='op', target=None, cycles=4)
    if z == 4:
        a = b(1) | (b(2) << 8)
        return dict(len=3, text='call %s,%04Xh' % (CC[y], a), kind='callc', target=a, cycles=10, cc=CC[y])
    if z == 5:
        if q == 0: return dict(len=plen, text='push %s' % (HL if p == 2 else R16AF[p]), kind='op', target=None, cycles=11 if not pre else 15)
        if p == 0: a = b(1) | (b(2) << 8); return dict(len=3, text='call %04Xh' % a, kind='call', target=a, cycles=17)
    if z == 6:
        return dict(len=plen + 1, text='%s%02Xh' % (ALU[y], n8()), kind='op', target=None, cycles=7)
    if z == 7: return dict(len=1, text='rst %02Xh' % (y * 8), kind='rst', target=y * 8, cycles=11)
    return dict(len=1, text='db %02Xh' % op, kind='op', target=None, cycles=4)

def flow(m, entries):
    """flow walk: reachable instruction addresses from the entry points -> dict addr -> decoded"""
    seen = {}; todo = list(entries)
    while todo:
        a = todo.pop()
        while a not in seen and 0 <= a < 0x2000:
            d = decode(m, a); seen[a] = d; k = d['kind']; nxt = a + d['len']
            if k in ('jr', 'jp'): todo.append(d['target']); break
            if k in ('jrc', 'jpc', 'djnz', 'callc', 'call'):
                todo.append(d['target'])
            if k in ('ret', 'jpind', 'halt'): break
            a = nxt
    return seen

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    start = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1F6000
    size = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x1F80
    mem = bytearray(0x10000); mem[:size] = rom[start:start + size]
    seen = flow(mem, [0])
    kinds = {}
    for a, d in seen.items(): kinds[d['kind']] = kinds.get(d['kind'], 0) + 1
    print('reachable instructions: %d, last address %04X, kinds %s' % (len(seen), max(seen), kinds))
    if '-l' in sys.argv:
        for a in sorted(seen): print('%04X  %s' % (a, seen[a]['text']))
