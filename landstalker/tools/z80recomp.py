#!/usr/bin/env python3
"""z80recomp.py ROM OUT.c [start_hex=1F6000] [size_hex=1F80]  -- Z80 -> C recompiler for the game's sound driver (2026-10-28, docs/SOUND_PLAN.md step 3).
Reads the driver image from the user's ROM, flow-walks it with tools/z80dis.py and writes `z80drv_step(Z80S *s)`: a switch on s->pc, one case per reachable instruction, each executing
that instruction (registers / flags / cycles like the Z80, helpers in tools/z80rt.h) and setting the next pc.  The generated file is derived from the ROM: NEVER commit it.
Self modifying instructions (the driver writes `ld (nn),a` into the immediate of a `ld b, n`) are found statically and read their immediate from memory at run time.
Only the instruction forms the driver uses are supported; anything else stops the generator (add the form + the fuzz test tools/z80test/)."""
import re, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
import z80dis

R8 = {'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e', 'h': 'h', 'l': 'l'}
PAIR = {'bc': ('BC()', 'SET_BC'), 'de': ('DE()', 'SET_DE'), 'hl': ('HL()', 'SET_HL'), 'af': ('AF()', 'SET_AF')}
CCOND = {'nz': '!(s->f & FZ)', 'z': '(s->f & FZ)', 'nc': '!(s->f & FC)', 'c': '(s->f & FC)', 'po': '!(s->f & FP)', 'pe': '(s->f & FP)', 'p': '!(s->f & FS)', 'm': '(s->f & FS)'}
ALUF = {'add a,': 's->a = add8_(s, V, 0)', 'adc a,': 's->a = add8_(s, V, s->f & FC)', 'sub ': 's->a = sub8_(s, V, 0)', 'sbc a,': 's->a = sub8_(s, V, s->f & FC)',
        'and ': 'and8_(s, V)', 'xor ': 'xor8_(s, V)', 'or ': 'or8_(s, V)', 'cp ': 'cp8_(s, V)'}

def num(t): return int(t.rstrip('h'), 16)

def operand(t, smc_imm=None):
    """C expression for an 8 bit source operand text"""
    t = t.strip()
    if t in R8: return 's->%s' % t
    if t == '(hl)': return 'RB(HL())'
    m = re.fullmatch(r'\((ix|iy)([+-]\d+)\)', t)
    if m: return 'RB(s->%s + (%s))' % (m.group(1), m.group(2))
    if re.fullmatch(r'[0-9A-F]{2}h', t): return '0x%s' % t[:-1]
    raise SystemExit('unsupported operand ' + t)

def dest(t, val):
    t = t.strip()
    if t in R8: return 's->%s = %s;' % (t, val)
    if t == '(hl)': return 'WB(HL(), %s);' % val
    m = re.fullmatch(r'\((ix|iy)([+-]\d+)\)', t)
    if m: return 'WB(s->%s + (%s), %s);' % (m.group(1), m.group(2), val)
    raise SystemExit('unsupported destination ' + t)

def emit(a, d, smc):
    t = d['text']; n = d['len']; cyc = d['cycles']; nxt = (a + n) & 0xFFFF; k = d['kind']
    body = []; pc = 'x%04X' % nxt
    def fin(extra_cyc=None, pcexpr=None):
        body.append('s->cyc += %d; s->pc = %s; return;' % (extra_cyc if extra_cyc is not None else cyc, pcexpr or '0x%04X' % nxt))
    if t == 'nop': fin()
    elif t == 'di': body.append('s->iff1 = s->iff2 = 0;'); fin()
    elif t == 'exx':
        body.append('SWAP8(s->b, s->b2); SWAP8(s->c, s->c2); SWAP8(s->d, s->d2); SWAP8(s->e, s->e2); SWAP8(s->h, s->h2); SWAP8(s->l, s->l2);'); fin()
    elif t == 'ex de,hl': body.append('SWAP8(s->d, s->h); SWAP8(s->e, s->l);'); fin()
    elif t == "ex af,af'": body.append('SWAP8(s->a, s->a2); SWAP8(s->f, s->f2);'); fin()
    elif t == 'neg': body.append('neg_(s);'); fin()
    elif t in ('rlca', 'rrca', 'rla', 'rra'): body.append('%s_(s);' % t); fin()
    elif k == 'jr': fin(pcexpr='0x%04X' % d['target'])
    elif k == 'jp': fin(pcexpr='0x%04X' % d['target'])
    elif k == 'jrc':
        body.append('if (%s) { s->cyc += 12; s->pc = 0x%04X; return; }' % (CCOND[d['cc']], d['target'])); fin(7)
    elif k == 'jpc':
        body.append('if (%s) { s->pc = 0x%04X; } else { s->pc = 0x%04X; } s->cyc += 10; return;' % (CCOND[d['cc']], d['target'], nxt))
    elif k == 'djnz':
        body.append('s->b--; if (s->b) { s->cyc += 13; s->pc = 0x%04X; return; }' % d['target']); fin(8)
    elif k == 'call': body.append('s->cyc += 17; push_(s, 0x%04X);' % nxt); fin(0, pcexpr='0x%04X' % d['target'])
    elif k == 'callc':
        body.append('s->cyc += 10; if (%s) { push_(s, 0x%04X); s->cyc += 7; s->pc = 0x%04X; return; }' % (CCOND[d['cc']], nxt, d['target'])); fin(0)
    elif k == 'ret': body.append('s->pc = pop_(s); s->cyc += 10; return;')
    elif k == 'retc':
        body.append('if (%s) { s->pc = pop_(s); s->cyc += 11; return; }' % CCOND[d['cc']]); fin(5)
    else:
        m = re.fullmatch(r'push (bc|de|hl|af|ix|iy)', t)
        if m:
            r = m.group(1); body.append('push_(s, %s);' % (PAIR[r][0] if r in PAIR else 's->' + r)); fin(); return body
        m = re.fullmatch(r'pop (bc|de|hl|af|ix|iy)', t)
        if m:
            r = m.group(1); body.append('{ uint16_t v = pop_(s); %s }' % (PAIR[r][1] + '(v);' if r in PAIR else 's->%s = v;' % r)); fin(); return body
        m = re.fullmatch(r'ld (a|b|c|d|e|h|l),(.+)', t)
        if m and not re.fullmatch(r'\([0-9A-F]+h\)', m.group(2)) and m.group(2) not in ('(bc)', '(de)'):
            if a in smc and m.group(2).endswith('h') and re.fullmatch(r'[0-9A-F]{2}h', m.group(2)):
                body.append('s->%s = RB(0x%04X);   /* self modifying: the immediate is read from memory */' % (m.group(1), a + 1))
            else: body.append(dest(m.group(1), operand(m.group(2))))
            fin(); return body
        m = re.fullmatch(r'ld (\(hl\)|\((?:ix|iy)[+-]\d+\)),(a|b|c|d|e|h|l)', t)
        if m: body.append(dest(m.group(1), 's->' + m.group(2))); fin(); return body
        m = re.fullmatch(r'ld a,\(([0-9A-F]+)h\)', t)
        if m: body.append('s->a = RB(0x%s);' % m.group(1)); fin(); return body
        m = re.fullmatch(r'ld \(([0-9A-F]+)h\),a', t)
        if m: body.append('WB(0x%s, s->a);' % m.group(1)); fin(); return body
        m = re.fullmatch(r'ld a,\((bc|de)\)', t)
        if m: body.append('s->a = RB(%s);' % PAIR[m.group(1)][0]); fin(); return body
        m = re.fullmatch(r'ld \(([0-9A-F]+)h\),(hl|de|bc)', t)
        if m: body.append('ww_(s, 0x%s, %s);' % (m.group(1), PAIR[m.group(2)][0])); fin(); return body
        m = re.fullmatch(r'ld (hl|de|bc),\(([0-9A-F]+)h\)', t)
        if m: body.append('%s(rw_(s, 0x%s));' % (PAIR[m.group(1)][1], m.group(2))); fin(); return body
        m = re.fullmatch(r'ld (bc|de|hl),([0-9A-F]{4})h', t)
        if m: body.append('%s(0x%s);' % (PAIR[m.group(1)][1], m.group(2))); fin(); return body
        m = re.fullmatch(r'ld (sp|ix|iy),([0-9A-F]{4})h', t)
        if m: body.append('s->%s = 0x%s;' % (m.group(1), m.group(2))); fin(); return body
        for pre, f in ALUF.items():
            if t.startswith(pre):
                v = operand(t[len(pre):], None)
                body.append(f.replace('V', v) + ';'); fin(); return body
        m = re.fullmatch(r'(inc|dec) (a|b|c|d|e|h|l|\(hl\)|\((?:ix|iy)[+-]\d+\))', t)
        if m:
            fn = 'inc8_' if m.group(1) == 'inc' else 'dec8_'
            body.append(dest(m.group(2), '%s(s, %s)' % (fn, operand(m.group(2))))); fin(); return body
        m = re.fullmatch(r'(inc|dec) (bc|de|hl)', t)
        if m:
            r = m.group(2); body.append('%s(%s %s 1);' % (PAIR[r][1], PAIR[r][0], '+' if m.group(1) == 'inc' else '-')); fin(); return body
        m = re.fullmatch(r'add (hl|ix),(bc|de|hl|ix|sp)', t)
        if m:
            tgt = m.group(1); src = m.group(2)
            sv = 's->ix' if src == 'ix' and tgt == 'ix' else PAIR[src][0] if src in PAIR else 's->sp'
            if tgt == 'hl': body.append('SET_HL(add16_(s, HL(), %s));' % sv)
            else: body.append('s->ix = add16_(s, s->ix, %s);' % sv)
            fin(); return body
        m = re.fullmatch(r'sbc hl,(bc|de|hl)', t)
        if m: body.append('SET_HL(sbc16_(s, HL(), %s));' % PAIR[m.group(1)][0]); fin(); return body
        m = re.fullmatch(r'bit (\d),(a|b|c|d|e|h|l)', t)
        if m: body.append('bit_(s, %s, s->%s);' % (m.group(1), m.group(2))); fin(); return body
        m = re.fullmatch(r'res (\d),(a|b|c|d|e|h|l)', t)
        if m: body.append('s->%s &= ~(1 << %s);' % (m.group(2), m.group(1))); fin(); return body
        m = re.fullmatch(r'rr (a|b|c|d|e|h|l)', t)
        if m: body.append('s->%s = rr8_(s, s->%s);' % (m.group(1), m.group(1))); fin(); return body
        m = re.fullmatch(r'srl (a|b|c|d|e|h|l)', t)
        if m: body.append('s->%s = srl8_(s, s->%s);' % (m.group(1), m.group(1))); fin(); return body
        raise SystemExit('unsupported instruction %04X: %s' % (a, t))
    return body

def pre_cycles(body):
    """GPGX's Z80 core adds an instruction's cycles BEFORE its memory accesses run: a write to the YM2612 / PSG sees the time after the instruction, so the generated code does the same
    (branch instructions keep adding at the end: their extra cycles depend on the outcome and they touch no chip)."""
    if body and re.match(r's->cyc \+= (\d+); s->pc = (0x[0-9A-F]+); return;$', body[-1]):
        m = re.match(r's->cyc \+= (\d+); s->pc = (0x[0-9A-F]+); return;$', body[-1])
        return ['s->cyc += %s;' % m.group(1)] + body[:-1] + ['s->pc = %s; return;' % m.group(2)]
    return body

def smc_sites(seen):
    out = set()
    for a, d in seen.items():
        m = re.fullmatch(r'ld \(([0-9A-F]+)h\),a', d['text'])
        if m:
            x = int(m.group(1), 16)
            if (x - 1) in seen and re.fullmatch(r'ld [abcdehl],[0-9A-F]{2}h', seen[x - 1]['text']): out.add(x - 1)
    return out

def main():
    rom = open(sys.argv[1], 'rb').read(); out = sys.argv[2]
    start = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x1F6000
    size = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x1F80
    mem = bytearray(0x10000); mem[:size] = rom[start:start + size]
    seen = z80dis.flow(mem, [0]); smc = smc_sites(seen)
    L = ['/* GENERATED by tools/z80recomp.py from the user\'s ROM: derived from game code, never commit. */', '#include "z80rt.h"', 'void z80drv_step(Z80S *s) {', '  switch (s->pc) {']
    for a in sorted(seen):
        L.append('  case 0x%04X: {   /* %s */' % (a, seen[a]['text']))
        bd = emit(a, seen[a], smc)
        if seen[a]['kind'] == 'op': bd = pre_cycles(bd)
        for ln in bd: L.append('    ' + ln)
        L.append('  }')
    L += ['  default: s->bad = 1; return;', '  }', '}', '']
    open(out, 'w').write('\n'.join(L))
    print('%d instructions, self modifying immediates at %s -> %s' % (len(seen), ' '.join('%04X' % x for x in sorted(smc)), out))
if __name__ == '__main__': main()
