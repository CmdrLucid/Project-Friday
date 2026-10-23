#!/usr/bin/env python3
"""roomgraph.py ROM [--dot out.dot] [--check]   -- reads the room connection graph from the ROM (S3.4, docs/STAGE3_INVENTORY.md).

Tables (US ROM, formats from Dinopony/landstalker-lib `world_rom_reader.cpp`, checked here against the game's own floor type bytes and the room sequences of recordings):
 * map connections `$11CEA2` .. `$11EA64`, 8 bytes each, ended by `$FFFF`: word (room 1 | extra bits << 10), x1, y1, word (room 2 | extra bits << 10), x2, y2.  Both directions use the same record
   (room 1 at x1 / y1 <-> room 2 at x2 / y2).  Extra bits: 0x01 initially closed, 0x02 NE, 0x04 NW, 0x08 ?, 0x10 NE stairs, 0x20 NW stairs.
 * room variants `$00A3D8`: 6 bytes (room, variant room, flag byte, flag bit): the variant is loaded instead while the story flag is set (`GetOriginalRoomNum`).
 * fall destinations `$00A1A8`, climb destinations `$00A35A` (ladders / holes): 4 / 6 byte tables, printed raw.
 * room entities: offset table `$01B090` (word per room, 0 = none) + entity records `$01B932 + offset - 1`, 8 bytes each, ended by `$FFFF` (x, y, z, orientation, type id, behaviour ...).
Use as a module: `import roomgraph; g = roomgraph.read(rom)` -> dict(conns=[...], variants=[...], entities={room: [...]}); see main for the checks.
--check: floor types at the connection cells (door / stairs bytes of the height map, via romroom.py) and, with `--chk FILE ...`, how many room changes of recordings (`rec_*.chk` / docs/replays/*.chk, column 2 = room) the table explains."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def rw(rom, a): return (rom[a] << 8) | rom[a + 1]

def read(rom):
    conns = []
    a = 0x11CEA2
    while rw(rom, a) != 0xFFFF and a < 0x11EA64:
        w1, w2 = rw(rom, a), rw(rom, a + 4)
        conns.append(dict(r1=w1 & 0x3FF, e1=(rom[a] & 0xFC) >> 2, x1=rom[a + 2], y1=rom[a + 3],
                          r2=w2 & 0x3FF, e2=(rom[a + 4] & 0xFC) >> 2, x2=rom[a + 6], y2=rom[a + 7], addr=a))
        a += 8
    variants = []
    a = 0x00A3D8
    while a < 0x00A61C and rw(rom, a) != 0xFFFF:
        variants.append(dict(room=rw(rom, a), variant=rw(rom, a + 2), flag_byte=rom[a + 4], flag_bit=rom[a + 5])); a += 6
    ents = {}
    for room in range(0, (0x01B6F0 - 0x01B090) // 2):
        off = rw(rom, 0x01B090 + 2 * room)
        if off == 0: continue
        a = 0x01B932 + off - 1; lst = []
        while rw(rom, a) != 0xFFFF and len(lst) < 16:
            b = rom[a:a + 8]
            lst.append(dict(x=b[0] & 0x3F, orient=b[0] >> 6, y=b[1] & 0x3F, palette=b[1] >> 6, z=b[6] & 0x0F, half_x=bool(b[3] & 0x80), half_y=bool(b[3] & 0x40),
                            type=b[5], dialogue=b[4] >> 2, speed=b[2] & 7, fightable=bool(b[2] & 0x80), liftable=bool(b[2] & 0x40), talkable=bool(b[2] & 0x20), behaviour=b[7] | ((b[4] & 3) << 8)))
            a += 8
        ents[room] = lst
    return dict(conns=conns, variants=variants, entities=ents)

def neighbours(g):
    nb = {}
    for c in g['conns']:
        nb.setdefault(c['r1'], []).append((c['r2'], c)); nb.setdefault(c['r2'], []).append((c['r1'], c))
    return nb

def main():
    import romroom
    rom = open(sys.argv[1], 'rb').read()
    g = read(rom)
    print('%d connections, %d variants, entities in %d rooms' % (len(g['conns']), len(g['variants']), len(g['entities'])))
    kinds = {}
    for c in g['conns']:
        k = ('stairs' if (c['e1'] | c['e2']) & 0x30 else 'door') + (' closed' if (c['e1'] | c['e2']) & 1 else '')
        kinds[k] = kinds.get(k, 0) + 1
    print('kinds:', kinds)
    if '--dot' in sys.argv:
        out = sys.argv[sys.argv.index('--dot') + 1]
        with open(out, 'w') as f:
            f.write('graph rooms {\n')
            for c in g['conns']: f.write('  r%d -- r%d;\n' % (c['r1'], c['r2']))
            f.write('}\n')
        print('wrote', out)
    if '--check' in sys.argv:
        cache = {}
        def hm(room):
            if room not in cache:
                try: cache[room] = romroom.arrays(romroom.decode(rom, room))['HM']
                except Exception: cache[room] = None
            return cache[room]
        stat = {}
        for c in g['conns']:
            for side in (1, 2):
                room, x, y = c['r%d' % side], c['x%d' % side], c['y%d' % side]
                h = hm(room)
                if h is None: stat['undecodable'] = stat.get('undecodable', 0) + 1; continue
                # the stream's height map cell (x, y) is RAM cell (x + 12, y + 12); the connection position is in RAM cell coordinates
                v = h.get((x - 12, y - 12), 0); t = v & 0xFF
                kind = 'door/stairs type' if t in (1, 2, 3, 4, 5, 6, 0x0B, 0x0C, 0x26, 0x27) else ('other %02X' % t)
                stat[kind] = stat.get(kind, 0) + 1
        print('floor type byte of the height map cell at every connection position (RAM cell coordinates):', sorted(stat.items(), key=lambda kv: -kv[1])[:12])
    if '--seam' in sys.argv:
        r = seamless(rom, g)
        print('seamless candidates:', {k: len(v) for k, v in r.items()})
    if '--chk' in sys.argv:
        check_sequences(g, sys.argv[sys.argv.index('--chk') + 1:])

def check_sequences(g, files):
    """room changes in checkpoint logs (columns: frame room ...; a checkpoint every 120 frames, so a change may hide intermediate rooms) explained by a connection / variant"""
    nb = neighbours(g)
    orig = {}   # a variant room (loaded while a story flag is set) uses the connections of the room it replaces (GetOriginalRoomNum)
    for v in g['variants']: orig.setdefault(v['variant'], set()).add(v['room'])
    def origs(r): return {r} | orig.get(r, set())
    ok = bad = skipped = 0; unexplained = []
    for fn in files:
        prev = None
        for line in open(fn):
            t = line.split()
            if len(t) < 3 or not t[1].isdigit(): continue
            r = int(t[1])
            if r == 0: continue
            if prev is not None and r != prev:
                def adj(a, b): return any(n in origs(b) or origs(n) & origs(b) for o in origs(a) for n, _ in nb.get(o, []))
                direct = adj(prev, r)
                two = any(adj(n, r) for o in origs(prev) for n, _ in nb.get(o, []))   # a room passed between two checkpoints
                if direct: ok += 1
                elif two: skipped += 1
                else: bad += 1; unexplained.append((os.path.basename(fn), prev, r))
            prev = r
    print('room changes in %d logs: %d explained by one connection / variant, %d by two (a room passed between checkpoints), %d NOT explained: %s' % (len(files), ok, skipped, bad, unexplained[:12]))

def seamless(rom, g):
    """which connections could be crossed without a fade: both cells are door cells (floor types 01 / 02 / 03 / 04 / 06) at the same floor height (low nibble of height map byte 0), no stairs / closed flag.
    Everything else (stairs, ladders, warp pads, locked doors, one-way scripts, different heights) keeps the game's fade (user decision 2026-10-23)."""
    import romroom
    cache = {}
    def hm(room):
        if room not in cache:
            try: cache[room] = romroom.arrays(romroom.decode(rom, room))['HM']
            except Exception: cache[room] = None
        return cache[room]
    doors = (1, 2, 3, 4, 6)   # floor types: 01 NE, 02 SE, 03 SW, 04 NW, 06 plain door (the arrival side of most connections: record = a directed door 01 / 04 on one side, a type 06 cell on the other)
    res = {'level door': [], 'height differs': [], 'not both doors': [], 'stairs / closed flag': [], 'undecodable': []}
    for c in g['conns']:
        if (c['e1'] | c['e2']) & 0x31: res['stairs / closed flag'].append(c); continue
        a, b = hm(c['r1']), hm(c['r2'])
        if a is None or b is None: res['undecodable'].append(c); continue
        va, vb = a.get((c['x1'] - 12, c['y1'] - 12), 0), b.get((c['x2'] - 12, c['y2'] - 12), 0)
        ta, tb = va & 0xFF, vb & 0xFF
        if ta not in doors or tb not in doors: res['not both doors'].append(c); continue
        if (va >> 8) & 15 != (vb >> 8) & 15: res['height differs'].append(c); continue
        res['level door'].append(c)
    return res

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    main()
