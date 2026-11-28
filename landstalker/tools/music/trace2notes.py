#!/usr/bin/env python3
# trace2notes.py TRACE OUT.json [FROM_FRAME]: LANDSTALKER_SNDTRACE (YM2612 + PSG writes) -> notes per channel
#   FM ch 0..5: key on/off (reg $28), pitch from $A0..$A6 (fnum + block), loudness from the carrier TL ($4C + ch / op4) and the patch id
#   (hash of the channel's operator registers $30..$9F + $B0) so instrument changes are visible; DAC (reg $2A/$2B) = drum hits (count only)
#   PSG ch 0..2 tone (period -> pitch, attenuation -> loudness), ch 3 noise
import sys, json, math
import os
OLD = os.environ.get('T2N_OLD') == '1'
TR, OUT = sys.argv[1], sys.argv[2]; F0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
YMCLK, PSGCLK, MCF = 7670453.0, 3579545.0, 896040.0
def tsec(fr, cy): return (fr - F0 + cy / MCF) / 59.922
reg = [[0] * 256, [0] * 256]; addr = [0, 0]
fm_on = [None] * 6; notes = []; dac_on = False; dac_hits = []
psg_per = [0] * 4; psg_att = [15] * 4; psg_latch = 0; psg_on = [None] * 4
def fm_pitch(ch):
    part, c = (0, ch) if ch < 3 else (1, ch - 3)
    lo = reg[part][0xA0 + c]; hi = reg[part][0xA4 + c]; fnum = ((hi & 7) << 8) | lo; blk = (hi >> 3) & 7
    if fnum == 0: return None
    f = fnum * (2 ** (blk - 1)) * (YMCLK / 144.0) / (2 ** 20)
    return 69 + 12 * math.log2(f / 440.0)
def fm_patch(ch):
    part, c = (0, ch) if ch < 3 else (1, ch - 3)
    vals = [reg[part][r + c] for r in range(0x30, 0xA0, 4) if not (0x40 <= r < 0x50)] + [reg[part][0xB0 + c]]
    return "%08x" % (hash(tuple(vals)) & 0xffffffff)
def fm_vel(ch):
    part, c = (0, ch) if ch < 3 else (1, ch - 3)
    tl = reg[part][0x4C + c] & 0x7F
    return max(1, min(127, int(127 * 10 ** (-0.75 * tl / 20.0))))
def close_fm(ch, t):
    o = fm_on[ch]
    if o and o["p"] is not None: o["t1"] = t; notes.append(o)
    fm_on[ch] = None
def psg_pitch(ch):
    n = psg_per[ch]
    if n <= 0: return None
    return 69 + 12 * math.log2(PSGCLK / (32.0 * n) / 440.0)
def psg_update(ch, t):
    o = psg_on[ch]; att = psg_att[ch]; p = psg_pitch(ch) if ch < 3 else ("noise", psg_per[3])
    sounding = att < 15 and p is not None
    if o and sounding and o["p"] == p:   # same pitch, only the volume envelope moves: the same note (keep the loudest)
        if att < o["att"]: o["att"] = att; o["v"] = max(1, int(127 * 10 ** (-2 * att / 20.0)))
        return
    if o and (not sounding or o["p"] != p):
        o["t1"] = t; notes.append(o); psg_on[ch] = None; o = None
    if sounding and not o:
        psg_on[ch] = {"ch": "psg%d" % ch, "t0": t, "p": p, "att": att, "v": max(1, int(127 * 10 ** (-2 * att / 20.0)))}
last_t = 0
for line in open(TR):
    f = line.split()
    if not f: continue
    if f[0] == "Y":
        fr, cy, port, val = int(f[1]), int(f[3]), int(f[4]), int(f[5], 16); t = tsec(fr, cy); last_t = t
        if fr < F0: pass
        part = port >> 1
        if port & 1 == 0: addr[part] = val; continue
        a = addr[part]; reg[part][a] = val
        if part == 0 and a == 0x28:
            c = val & 7; ch = c if c < 4 else c - 1
            if c == 3 or ch > 5: continue
            if val & 0xF0:
                close_fm(ch, t)
                if fr >= F0: fm_on[ch] = {"ch": "fm%d" % ch, "t0": t, "p": fm_pitch(ch), "v": fm_vel(ch), "patch": fm_patch(ch)}
            else: close_fm(ch, t)
        elif part == 0 and a == 0x2B: dac_on = bool(val & 0x80)
        elif part == 0 and a == 0x2A and fr >= F0: dac_hits.append(t)
        elif a in (0xA0, 0xA1, 0xA2) and fm_on[a - 0xA0 + 3 * part]:   # pitch change while held (slide / vibrato): keep the note's first pitch, note the range
            ch = a - 0xA0 + 3 * part; o = fm_on[ch]; p = fm_pitch(ch)
            if p is not None and o["p"] is not None and abs(p - o["p"]) > 0.5 and not OLD:   # a new pitch WITHOUT a new key on (arpeggios of fm3): a new note
                if t - o["t0"] < 0.004 and not OLD: o["p"] = p                               # set right after the key on: the note's real pitch
                else:
                    o["t1"] = t; notes.append(o); fm_on[ch] = {"ch": o["ch"], "t0": t, "p": p, "v": o["v"], "patch": o["patch"], "legato": 1}
    elif f[0] == "P":
        fr, cy, val = int(f[1]), int(f[3]), int(f[4], 16); t = tsec(fr, cy)
        if val & 0x80:
            psg_latch = (val >> 5) & 3
            if val & 0x10: psg_att[psg_latch] = val & 15
            else: psg_per[psg_latch] = (psg_per[psg_latch] & 0x3F0) | (val & 15)
        else:
            psg_per[psg_latch] = (psg_per[psg_latch] & 0x0F) | ((val & 0x3F) << 4)
        if fr >= F0: psg_update(psg_latch, t)
for ch in range(6): close_fm(ch, last_t)
for ch in range(4):
    if psg_on[ch]: psg_on[ch]["t1"] = last_t; notes.append(psg_on[ch])
notes = [n for n in notes if n["t0"] >= 0 and n["t1"] - n["t0"] > 0.005]
# DAC hits: merge sample streams (one hit = a burst of writes) into onsets
on = [];
for t in dac_hits:
    if not on or t - on[-1][1] > 0.03: on.append([t, t])
    else: on[-1][1] = t
json.dump({"notes": notes, "dac": [a for a, b in on]}, open(OUT, "w"))
from collections import Counter
c = Counter(n["ch"] for n in notes); print("notes per channel:", dict(c), " DAC onsets:", len(on))
for ch in sorted(c):
    ps = [n["p"] for n in notes if n["ch"] == ch and isinstance(n["p"], float)]
    pt = Counter(n.get("patch") for n in notes if n["ch"] == ch)
    if ps: print(" %-5s pitch %.1f..%.1f  patches %s" % (ch, min(ps), max(ps), dict(pt) if ch.startswith("fm") else ""))
