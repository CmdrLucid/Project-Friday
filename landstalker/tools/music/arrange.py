#!/usr/bin/env python3
# arrange.py NOTES.json OUT.mid : orchestral arrangement of the Massan theme from the chip notes (trace2notes.py)
# roles (heard from the note lists): fm0 melody, fm4 = echo of the melody (dropped: the reverb does that), fm3 arpeggios, fm1 bass,
# fm2 counter melody (from 7.8 s), psg0 / psg1 off-beat chord pulses.
import sys, json, mido
d = json.load(open(sys.argv[1])); notes = d["notes"]; OUT = sys.argv[2]
TPB, BPM = 480, 125.0
def tick(t): return int(round(t * BPM / 60.0 * TPB))
# part: (source channel, MIDI channel, GM program, octave shift, velocity range, length mode, length cap s)
PRESETS = {
 "v1": [("fm0", 0, 48, 0, (70, 100), "legato", 1.6), ("fm0", 1, 73, 12, (55, 80), "legato", 1.2), ("fm2", 2, 68, 0, (55, 80), "legato", 1.0),
        ("fm3", 3, 46, 0, (50, 75), "ring", 0.7), ("fm1", 4, 43, 0, (70, 95), "legato", 0.9), ("fm1", 5, 45, 12, (40, 60), "short", 0.2),
        ("psg0", 6, 45, 0, (40, 60), "short", 0.2), ("psg1", 6, 45, 0, (35, 55), "short", 0.2), ("psg0", 7, 60, -12, (30, 45), "hold", 0.45)],
 # v2 (user 2026-11-28: 'zu hallig, zu durcheinander'): fewer voices, a solo violin melody (the string section's slow attack smeared the fast notes),
 # softer harp / counter melody, one pulse channel, no doublings / pad
 "v2": [("fm0", 0, 40, 0, (75, 105), "legato", 0.8), ("fm2", 2, 68, 0, (45, 65), "legato", 0.7),
        ("fm3", 3, 46, 0, (32, 52), "ring", 0.4), ("fm1", 4, 43, 0, (60, 85), "legato", 0.6),
        ("psg0", 6, 45, 0, (28, 42), "short", 0.15)],
 # v3 (user: 'Violine penetrant, Hintergrund unruhig'): flute melody, soft clarinet counter melody, bass; the busy arpeggios + pulses become
 # held string chords (PADS below: pitch classes of fm3 / psg0 / psg1 per 2 beats, 3 voices around middle C)
 "v3": [("fm0", 0, 73, 0, (62, 90), "legato", 0.9), ("fm2", 2, 71, 0, (34, 52), "legato", 0.7), ("fm1", 4, 43, 0, (52, 75), "legato", 0.6)],
}
PRESETS["v4"] = [("fm0", 0, 73, 0, (62, 90), "legato", 0.9), ("fm2", 2, 71, 0, (34, 52), "legato", 0.7), ("fm1", 4, 43, 0, (52, 75), "legato", 0.6),
                 ("psg0", 3, 49, 0, (40, 50), "sustain", 4.0), ("psg1", 5, 49, 0, (38, 48), "sustain", 4.0)]   # v4: the REAL accompaniment tones held (no guessed chords)
# v5: psg1 = an ECHO of psg0 (0.12 s later, softer) -> dropped; psg0 = low chord pulses (held strings) AND, in some sections, a high
# trill descant up to C7 (piccolo, short, soft) - split at MIDI 76
PRESETS["v5"] = [("fm0", 0, 73, 0, (62, 90), "legato", 0.9), ("fm2", 2, 71, 0, (34, 52), "legato", 0.7), ("fm1", 4, 43, 0, (52, 75), "legato", 0.6),
                 ("psg0", 3, 49, 0, (40, 50), "sustain", 4.0, {"pmax": 75.5}), ("psg0", 5, 72, 0, (30, 45), "legato", 0.3, {"pmin": 75.5})]
PADS = {"v3": {"src": ("fm3", "psg0", "psg1"), "ch": 3, "prog": 49, "vel": 46, "beat0": 0.07, "win_beats": 2}}
PARTS = PRESETS[sys.argv[3] if len(sys.argv) > 3 else "v1"]
events = []
for part in PARTS:
    src, mch, prog, octv, (v0, v1), mode, cap = part[:7]; flt = part[7] if len(part) > 7 else {}
    ns = sorted([n for n in notes if n["ch"] == src and isinstance(n["p"], float) and flt.get("pmin", -1) <= n["p"] <= flt.get("pmax", 999)], key=lambda n: n["t0"])
    if not ns: continue
    vs = [n["v"] for n in ns]; lo, hi = min(vs), max(vs)
    if mode == "sustain":   # repeated pulses of one pitch = one held tone until the pitch changes
        merged = []
        for n in ns:
            if merged and int(round(merged[-1]["p"])) == int(round(n["p"])) and n["t0"] - merged[-1]["t1"] < 0.6: merged[-1] = dict(merged[-1], t1=n["t1"])
            else: merged.append(dict(n))
        ns = merged
    for i, n in enumerate(ns):
        p = int(round(n["p"])) + octv
        nxt = next((m["t0"] for m in ns[i + 1:] if m["t0"] > n["t0"] + 0.01), n["t0"] + cap)
        if mode == "legato": dur = min(nxt - n["t0"], cap) * 0.97
        elif mode == "ring": dur = cap
        elif mode == "hold": dur = min(nxt - n["t0"], cap)
        elif mode == "sustain": dur = min(nxt - n["t0"], cap) * 0.98
        else: dur = cap
        dur = max(dur, n["t1"] - n["t0"] if mode != "short" else 0.05)
        v = v0 + (v1 - v0) * ((n["v"] - lo) / (hi - lo) if hi > lo else 0.5)
        events.append((tick(n["t0"]), 1, mch, p, int(v))); events.append((tick(n["t0"] + dur), 0, mch, p, 0))
pad = PADS.get(sys.argv[3] if len(sys.argv) > 3 else "v1")
if pad:
    from collections import defaultdict
    win = pad["win_beats"] * 60.0 / BPM; src = [n for n in notes if n["ch"] in pad["src"] and isinstance(n["p"], float)]
    end = max(n["t1"] for n in notes); k = 0; prev = None
    while pad["beat0"] + k * win < end:
        a = pad["beat0"] + k * win; b = a + win; w = defaultdict(float)
        for n in src:
            o = min(b, n["t1"] + 0.15) - max(a, n["t0"])
            if o > 0: w[int(round(n["p"])) % 12] += o
        for n in notes:                                              # the bass counts more (the chord root)
            if n["ch"] == "fm1" and isinstance(n["p"], float):
                o = min(b, n["t1"] + 0.15) - max(a, n["t0"])
                if o > 0: w[int(round(n["p"])) % 12] += 0.15 * o   # weak: the bass runs chromatic lines under held chords (Massan: C B A G# G under F)
        best, bs = None, -1e9
        for root in range(12):                                      # best major / minor triad for the window
            for third in (4, 3):
                tri = (root, (root + third) % 12, (root + 7) % 12)
                sc = sum(w[p] for p in tri) - 0.6 * sum(v for p, v in w.items() if p not in tri) + (0.02 if third == 4 else 0)
                if sc > bs: best, bs = tri, sc
        pcs = list(best) if w else []
        chord = sorted(55 + ((pc - 55) % 12) for pc in pcs)        # voices in 55..66 (G3..F#4)
        if chord and chord != prev:
            if prev: [events.append((tick(a), 0, pad["ch"], p, 0)) for p in prev]
            for p in chord: events.append((tick(a) + 1, 1, pad["ch"], p, pad["vel"]))
            prev = chord
        k += 1
    if prev: [events.append((tick(end), 0, pad["ch"], p, 0)) for p in prev]
    PARTS = PARTS + [("pad", pad["ch"], pad["prog"], 0, (0, 0), "", 0)]
mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
progs = {}
for src, mch, prog, *_ in PARTS: progs[mch] = prog
for mch, prog in progs.items():
    tr.append(mido.Message("program_change", channel=mch, program=prog, time=0))
    tr.append(mido.Message("control_change", channel=mch, control=91, value=70, time=0))   # reverb send (if the player uses it)
    tr.append(mido.Message("control_change", channel=mch, control=7, value=100, time=0))
pan = {0: 54, 1: 70, 2: 80, 3: 40, 4: 64, 5: 60, 6: 90, 7: 30}
for mch, v in pan.items(): tr.append(mido.Message("control_change", channel=mch, control=10, value=v, time=0))
events.sort(key=lambda e: (e[0], e[1]))
now = 0
for t, on, ch, p, v in events:
    if not (0 <= p < 128): continue
    tr.append(mido.Message("note_on" if on else "note_off", channel=ch, note=p, velocity=v, time=t - now)); now = t
mid.save(OUT); print(OUT, len(events) // 2, "notes")
