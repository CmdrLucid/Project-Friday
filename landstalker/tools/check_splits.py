#!/usr/bin/env python3
"""check_splits.py ROM [src/recomp]

Looks for generated functions that are cut off in the MIDDLE of an instruction ("Fall through to next function" into an address that is not the next
instruction boundary). Cause: a bogus function start (seed) inside real code splits it; the generated code then runs garbage / skips the rest.
Reports: function, end address given by the generator, where the last instruction really ends, and the fall-through target. Also lists seeds from recomp.json
that point into the middle of an instruction of another function."""
import sys, re, glob, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genc   # generated calls may use named constants (tools/rename_generated.py)
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
hdr = re.compile(r'^/\* \$([0-9A-F]{6})-\$([0-9A-F]{6})\s+\((\d+) instructions, (\d+) bytes\) \*/')


def find_bad(rom, d='src/recomp'):
    """-> (total functions scanned, [(name, start, end, tail, straddler_end, straddler_addr)])"""
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    bad = []; total = 0
    ex = genc.expand(d)
    for f in sorted(glob.glob(os.path.join(d, 'recomp_*.c'))):
        lines = [ex(l) for l in open(f).read().split('\n')]
        i = 0
        while i < len(lines):
            m = hdr.match(lines[i])
            if not m: i += 1; continue
            start, end = int(m.group(1), 16), int(m.group(2), 16)
            name = lines[i + 1].split('(')[0].replace('void ', '') if i + 1 < len(lines) else '?'
            j = i + 1; tail = None
            while j < len(lines) and not lines[j].startswith('}'):
                if 'Fall through to next function' in lines[j] and j + 1 < len(lines):
                    t = re.search(r'func_table_tail\(0x([0-9A-F]+)\)', lines[j + 1]); tail = int(t.group(1), 16) if t else None
                j += 1
            total += 1
            if tail is not None:
                # decode from the function start up to the generator's end address; if the last instruction crosses `end`, the next function starts INSIDE it
                a = start; last = None
                while a < max(end, tail) and a < len(rom) - 2:
                    ins = list(md.disasm(rom[a:a + 12], a, 1))
                    if not ins: break
                    nxt = a + ins[0].size
                    if a < tail < nxt:          # the fall-through target / next function starts INSIDE this instruction
                        bad.append((name, start, end, tail, nxt, a)); break
                    if a >= tail: break
                    last = a; a = nxt
            i = j
    return total, bad


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    d = sys.argv[2] if len(sys.argv) > 2 else 'src/recomp'
    total, bad = find_bad(rom, d)
    print('%d generated functions scanned; %d are cut off inside an instruction' % (total, len(bad)))
    for name, start, end, tail, a, last in bad:
        print('  %-14s $%06X-$%06X  last instruction at $%06X ends at $%06X, but the next function starts at $%06X (INSIDE it)' % (name, start, end, last, a, tail))
    if os.path.exists('recomp.json'):
        seeds = [int(k, 16) for k in json.load(open('recomp.json')).get('seeds', {})]
        print('%d seeds in recomp.json; ' % len(seeds), end='')
        hits = sorted(set(b[3] for b in bad))
        print('bogus split addresses:', ' '.join('$%06X' % h for h in hits[:40]))
        inseed = [h for h in hits if h in set(seeds)]
        print('of these listed as seeds in recomp.json:', ' '.join('$%06X' % h for h in inseed[:40]) or 'none')
