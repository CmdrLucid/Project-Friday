#!/usr/bin/env python3
"""jplang.py ROM OUTDIR -- the language 'Japanese' = the ORIGINAL Japanese text of 'Landstalker - Koutei no Zaihou', built on the player's machine from his own Japanese ROM
(user 2026-11-14: 'mach japanisch durch; die Sprache soll nur zur Auswahl stehen, wenn eine japanische ROM gefunden wurde').
 * The Japanese ROM is looked for in the folder of ROM (header region 'J', name LAND STALKER, 2 MB).  None -> OUTDIR/ja.bin is removed and 'ja' leaves OUTDIR/index.txt.
 * Text: the Japanese strings are decoded from that ROM (same Huffman scheme as tools/stringdump.py, Japanese tables: offsets $23C94, trees $23E8E, 8 bank pointers at $38532,
   string begin code $E9, controls $EA + k with the meanings of stringdump.CONTROL).  The game asks for the ENGLISH string ids, so lang/ja_map.json (shipped, numbers only)
   says which Japanese string(s) belong to each English id ("jp": [index, ...] in decode order, "part": [k, n] = piece k of n when the English release split one Japanese
   string).  Head ({Speaker}) and end codes come from the English string (the scripts expect them), the body (lines, pages, pauses, {Item} / {Number}) from the Japanese one;
   a string whose {Item} / {Number} count differs stays English.
 * Font: the glyphs of the Japanese main font ($2B4B8, 30 bytes each); kana with voicing marks (the Japanese ROM stores the mark BEFORE the kana and prints it as an
   own character) are composed into one glyph.  Codes: names (bytes) and the most frequent characters get $6C..$FF, the rest $101.. ; the low byte never hits a code the
   printer treats specially ($00 space, $7B / $7C marks), except on purpose: the speech bracket gets low byte $47 (CHR_BEGIN_TALK: speech blips start like in the
   Japanese game) and the ellipsis dot low byte $40 (CHR_ELLIPSIS_DOT: no blip).
 * Names: the character / special name tables of the Japanese ROM ($2A2EA / $2A3E4); item names stay English (the menus draw them with the 8x8 menu font, which has no kana).
 * Output: OUTDIR/ja.bin (LKLG version 3: glyph entries with a 16-bit code), line 'ja<TAB>Japanese' in OUTDIR/index.txt.  Local only (ROM-derived), like build/lang/*.bin."""
import json, os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stringdump as sd
import langbuild as lb

JP_HUFF_OFFS, JP_HUFF_TREES, JP_BANKS, JP_NBANKS, JP_BEGIN = 0x23C94, 0x23E8E, 0x38532, 8, 0xE9
JP_FONT, JP_NAMES = 0x2B4B8, (("char", 0x2A2EA, 61), ("special", 0x2A3E4, 15))
J_DAK, J_HANDAK, J_SPACE, J_DOT, J_TALK, J_YESNO = 123, 124, 0, 0xD8, 0xD9, 236
SKIP_EN = set(range(0x0000, 0x0004)) | set(range(0x001D, 0x004E))   # Yes / No / Use / Equip and the debug menus: drawn with the menu font -> stay English
HERE = os.path.dirname(os.path.abspath(__file__))
# order of the Japanese main font (code = index), only used for the few own lines of lang/ja_map.json ("text": English-only lines of the English release)
JP_CHARSET = ' 0123456789あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんぁぃぅぇぉゃゅょっアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンァィゥェォャュョッ、。゛゜ー!?※東西南北上中下道具屋教会宿神父冒険記録毒呪治療金貨枚買階本売泊客品男女子供人族殿公爵領主兵悪霊年月日財宝地図実灯台家店町村滝岬島海沼湖港城塔森橋団気船箱魔命危美長古老作名商大・「」↘↖↙↗王剣士国本法ABC.'



def is_jp(rom):
    return len(rom) == 0x200000 and rom[0x1F0:0x1F4].strip() == b'J' and b'LANDSTALKER' in rom[0x120:0x150].upper().replace(b' ', b'')


def find_jp(rompath):
    d = os.path.dirname(os.path.abspath(rompath)) if os.path.isfile(rompath) else rompath
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p) and os.path.getsize(p) == 0x200000:
            r = open(p, 'rb').read()
            if is_jp(r): return f, r
    return None, None


def jp_strings(rom):
    """-> list of code lists in decode order (bank by bank), like the Japanese string ids"""
    save = sd.HUFF_OFFS, sd.HUFF_TREES, sd.STR_BEGIN
    sd.HUFF_OFFS, sd.HUFF_TREES, sd.STR_BEGIN = JP_HUFF_OFFS, JP_HUFF_TREES, JP_BEGIN
    try:
        banks = [struct.unpack('>I', rom[JP_BANKS + 4 * i:JP_BANKS + 4 * i + 4])[0] for i in range(JP_NBANKS)]
        out = []
        for b, start in enumerate(banks):
            pos, idx = start, 0
            while idx < 256 and (b + 1 >= len(banks) or pos < banks[b + 1]) and rom[pos] != 0:
                codes, pos = sd.decode_codes(rom, pos); out.append(codes); idx += 1
        return out
    finally:
        sd.HUFF_OFFS, sd.HUFF_TREES, sd.STR_BEGIN = save


def jp_names(rom):
    res = {}
    for name, start, count in JP_NAMES:
        p = start
        for i in range(count):
            n = rom[p]; res['%s:%02d' % (name, i)] = list(rom[p + 1:p + 1 + n]); p += 1 + n
    # LK_JPITEMS v3: the item names follow (default name: 1 entry, then 64 items, $2A43A) like in the US ROM; in Japanese they are the DIALOGUE item names ({Item})
    p += 1 + rom[p]
    for i in range(64):
        n = rom[p]; res['item:%02d' % i] = list(rom[p + 1:p + 1 + n]); p += 1 + n
    return res


# a token list: ('g', jp code or (mark, code)) / ('c', k)
def tok(codes):
    out, mark = [], None
    for c in codes:
        if c >= 0xEA: out.append(('c', c - 0xEA)); continue
        if c in (J_DAK, J_HANDAK): mark = c; continue
        out.append(('g', (mark, c) if mark else c)); mark = None
    return out


K = {v: k for k, v in sd.CONTROL.items()}
END = {K['WaitInput'], K['ContinuePrompt'], K['NewLine'], K['NewLinePrompt']}
PAUSE = {K['Pause1s'], K['Pause1sOrInput'], K['Pause1_5sOrInput'], K['Pause2sOrInput']}


def body_of(codes):
    t = tok(codes)
    while t and t[0] in (('c', K['Speaker']),): t = t[1:]
    while t and (t[-1][0] == 'c' and t[-1][1] in END or t[-1] in (('g', J_YESNO), ('g', J_SPACE))): t = t[:-1]
    return t


def split_parts(t, n, weights):
    """cut a token list into n pieces at page / line / space boundaries near the proportional targets"""
    if n == 1: return [t]
    total = sum(weights); cuts = []; acc = 0
    cand = [i for i, x in enumerate(t) if x == ('c', K['ContinuePrompt'])] or []
    lines = [i for i, x in enumerate(t) if x == ('c', K['SoftNewLine'])]
    spaces = [i for i, x in enumerate(t) if x == ('g', J_SPACE)]
    for k in range(n - 1):
        acc += weights[k]; target = len(t) * acc / total
        best = None
        for pool, pen in ((cand, 0), (lines, 6), (spaces, 12)):
            for i in pool:
                if cuts and i <= cuts[-1]: continue
                d = abs(i - target) + pen
                if best is None or d < best[0]: best = (d, i)
        cuts.append(best[1] if best else int(target))
    out, s = [], 0
    for c in cuts + [len(t)]:
        piece = t[s:c]
        while piece and piece[0] in (('c', K['ContinuePrompt']), ('c', K['SoftNewLine']), ('g', J_SPACE)): piece = piece[1:]
        out.append(piece); s = c
    return out


def text_tokens(s):
    """own line (kana, '|' = line break, '#' = page break, {Pause1s} ...) -> tokens; voiced kana are split into mark + base like the ROM stores them"""
    import unicodedata
    out = []
    for part in re.findall(r'\{\w+\}|.', s):
        if part.startswith('{'): out.append(('c', K[part[1:-1]])); continue
        if part == '|': out.append(('c', K['SoftNewLine'])); continue
        if part == '#': out.append(('c', K['ContinuePrompt'])); continue
        d = unicodedata.normalize('NFD', part)
        if len(d) == 2 and d[1] in '\u3099\u309a': out.append(('g', (J_DAK if d[1] == '\u3099' else J_HANDAK, JP_CHARSET.index(d[0])))); continue
        out.append(('g', JP_CHARSET.index(part)))
    return out


def glyph(rom, c):
    b = rom[JP_FONT + 30 * c:JP_FONT + 30 * c + 30]
    return [b[2 * i] << 8 | b[2 * i + 1] for i in range(15)]


def compose(rom, g):
    if not isinstance(g, tuple): return glyph(rom, g)
    mark, c = g; r = glyph(rom, c); m = glyph(rom, mark)
    for i in range(4): r[i] |= (m[i] << 1) & 0xFFFF   # the Japanese printer draws the mark (4 rows) and steps back to 1 px after its start
    return r


def width(rows):
    last = -1
    for r in rows:
        for k in range(16):
            if r & (0x8000 >> k): last = max(last, k)
    return 8 if last < 0 else last + 3


def main():
    rompath, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    idxf = os.path.join(out, 'index.txt'); target = os.path.join(out, 'ja.bin')
    idx = [l for l in (open(idxf, encoding='utf-8').read().splitlines() if os.path.exists(idxf) else []) if l and not l.startswith('ja\t')]
    name, jrom = find_jp(rompath)
    if not jrom:
        if os.path.exists(target): os.remove(target)
        open(idxf, 'w', encoding='utf-8').write('\n'.join(idx) + ('\n' if idx else ''))
        print('jplang: no Japanese ROM next to %s: no Japanese language' % rompath); return
    us = open(rompath, 'rb').read(); en = sd.decode_all(us)
    jmap = json.load(open(os.path.join(HERE, '..', 'lang', 'ja_map.json'), encoding='utf-8'))
    js = jp_strings(jrom)
    # pieces per English id
    pieces, groups = {}, {}
    for k, v in jmap.items():
        if not k.startswith('0') and not re.fullmatch('[0-9A-F]{4}', k): continue
        if int(k, 16) in SKIP_EN or k not in en: continue
        if v.get('text'): pieces[k] = text_tokens(v['text']); continue
        if not v.get('jp'): continue
        groups.setdefault(tuple(v['jp']), []).append((v['part'][0], v['part'][1], k))
    for jl, members in groups.items():
        t = []
        for n_, j in enumerate(jl):
            if j >= len(js): t = None; break
            b = body_of(js[j])
            if n_: t += [('c', K['ContinuePrompt'])]
            t += b
        if t is None: continue
        members.sort(); n = max(m[1] for m in members)
        if len(members) != n: n = len(members)
        w = [max(8, len(re.sub(r'\{[^}]*\}', '', en[m[2]]))) for m in members]
        for (p, _, k), piece in zip(members, split_parts(t, n, w)): pieces[k] = piece
    # glyph codes: names first (bytes), then by frequency
    names = jp_names(jrom)
    freq = {}
    for p in pieces.values():
        for x in p:
            if x[0] == 'g' and x[1] != J_SPACE: freq[x[1]] = freq.get(x[1], 0) + 1
    name_gl = []
    for v in names.values():
        for x in tok(v):
            if x[0] == 'g' and x[1] != J_SPACE and x[1] not in name_gl: name_gl.append(x[1])
    order = name_gl + sorted((g for g in freq if g not in name_gl), key=lambda g: -freq[g])
    code, fixed = {J_SPACE: 0}, {J_TALK: 0x147, J_DOT: 0x140}
    code.update(fixed)
    free_lo = [c for c in range(0x6C, 0x100) if c not in (0x7B, 0x7C)]
    free_hi = [c for c in range(0x101, 0x800) if (c & 0xFF) not in (0x00, 0x40, 0x47, 0x7B, 0x7C)]
    for g in order:
        if g in code: continue
        code[g] = (free_lo or free_hi).pop(0)
    rows = {c: compose(jrom, g) for g, c in code.items() if c}
    W = {c: width(r) for c, r in rows.items()}; W[0] = 8
    # strings -> words (EN head / tail, Japanese body), line check
    HL = {k: lb.HANDLER[k] for k in range(len(lb.HANDLER))}
    strs, blob, kept, eng = [], bytearray(), 0, 0
    for k in sorted(pieces):
        e = en[k]; p = pieces[k]
        if e.count('{Item}') != sum(1 for x in p if x == ('c', K['Item'])) or e.count('{Number}') != sum(1 for x in p if x == ('c', K['Number'])):
            eng += 1; os.environ.get('JPLANG_V') and print('  stays English:', k); continue
        head = [('c', K['Speaker'])] if e.startswith('{Speaker}') else []
        if head and p and p[0] == ('g', J_TALK): p = p[1:]
        while p and p[-1][0] == 'c' and p[-1][1] in PAUSE: p = p[:-1]   # the English end decides the timing (auto-advancing cutscene lines end with pauses)
        m = re.search(r'((?:\{(?:ContinuePrompt|WaitInput|NewLine|NewLinePrompt|Pause1s|Pause1sOrInput|Pause1_5sOrInput|Pause2sOrInput)\})+)$', e)
        tail = [('c', K[x]) for x in re.findall(r'\{(\w+)\}', m.group(1))] if m else []
        words = []
        for x in head + p + tail:
            if x[0] == 'c': words.append(~HL[x[1]] & 0xFFFF)
            else: words.append(code[x[1]])
        strs.append((int(k, 16), len(blob), len(words))); blob += b''.join(struct.pack('>H', w) for w in words) + b'\xff\xff'; kept += 1
    nm = []
    for key, v in names.items():
        tab, i = key.split(':'); data = bytes(code.get(x[1], 0) if x[0] == 'g' else 0 for x in tok(v))
        if any(c > 0xFF for c in (code.get(x[1], 0) for x in tok(v) if x[0] == 'g')): print('jplang: name %s needs a glyph code > $FF: stays English' % key); continue
        # item names: index | $40 = only for {Item} in the dialogue (patch_lang.py lk_lg_inpc); the menus keep the English names (8x8 menu font)
        nm.append((lb.TABLES[tab], int(i) | (0x40 if tab == 'item' else 0), len(blob), len(data))); blob += data
    # LK_JPITEMS v2 (user 2026-11-13: 'im Englischen passt es, auf Japanisch ist es wieder das Spell Book'): item names stay English in Japanese (8x8 menu font, no kana),
    # so Options > Items = Japanese needs the English names of the four items here too (index | $80, ROM glyph codes < $6C = the same in ja.bin)
    eij = json.load(open(os.path.join(HERE, '..', 'lang', 'en_items.json'), encoding='utf-8')).get('items_jp', {}).get('names', {})
    for key, ent in eij.items():
        tab, i = key.split(':'); data = bytes(v for t, v in lb.tokens(ent['t']))
        assert all(c < 0x6C for c in data), key
        nm.append((lb.TABLES[tab], int(i) | 0x80, len(blob), len(data))); blob += data
    gl = sorted((c, r) for c, r in rows.items() if c)
    hdr = b'LKLG' + struct.pack('>HHHHHH', 3, len(strs), len(nm), 0, len(gl), 0)
    data = hdr + b''.join(struct.pack('>HIH', *s) for s in strs) + b''.join(struct.pack('>BBIB', *n) for n in nm)
    data += b''.join(struct.pack('>H', c) + lb.pack(r) + bytes(8) for c, r in gl) + bytes(blob)
    open(target, 'wb').write(data)
    idx.append('ja\tJapanese'); open(idxf, 'w', encoding='utf-8').write('\n'.join(idx) + '\n')
    print('jplang: %d Japanese strings (%d stay English: {Item} / {Number} differ), %d names, %d glyphs (highest code $%X) from %s -> %s'
          % (kept, eng, len(nm), len(gl), max(code.values()), name, target))


if __name__ == '__main__':
    main()
