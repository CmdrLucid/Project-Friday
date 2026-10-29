#!/usr/bin/env python3
"""sndtrace.py TRACE   -- summary of a LANDSTALKER_SNDTRACE file (tools/patch_sndtrace.py): commands, writes per frame, share of DAC writes, distinct commands."""
import sys, collections
f = open(sys.argv[1]); ym = collections.Counter(); regs = collections.Counter(); cmds = []; frames = set(); n = collections.Counter()
addr = [0, 0]; last_cyc_ym = None; dac = 0; ymn = 0; gaps = collections.Counter()
for ln in f:
    t = ln.split(); k = t[0]; n[k] += 1
    if k == 'Y':
        fr, who, cyc, port, val = int(t[1]), t[2], int(t[3]), int(t[4]), int(t[5], 16)
        ymn += 1
        if port in (0, 2): addr[port // 2] = val
        else:
            reg = addr[port // 2] | (0x100 if port == 3 else 0); regs[reg] += 1
            if reg == 0x2A: dac += 1
        frames.add(fr)
    elif k == 'M' and t[4] == '1FFF': cmds.append((int(t[1]), int(t[5], 16)))
print('lines', dict(n), 'frames with YM writes', len(frames))
print('YM data writes by register (top 12):', [('%03X' % r, c) for r, c in regs.most_common(12)])
print('DAC (reg $2A) share of YM data writes: %.1f %%' % (100.0 * dac / max(1, sum(regs.values()))))
print('commands to the Z80 (mailbox $1FFF): %d, distinct ids %d: %s' % (len(cmds), len(set(c for _, c in cmds)), sorted(set('%02X' % c for _, c in cmds))))
