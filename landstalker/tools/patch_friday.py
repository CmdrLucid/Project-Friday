#!/usr/bin/env python3
"""Friday Hints (2026-10-31, user: 'Karte + Hinweise ja', Select key, two levels; idea docs/MODERN_IDEAS.md (B)).  Press Select (pad Back = MD Mode, keyboard: the key
bound to Mode) while Nigel walks and Friday says where to go next, in the game's own text box; (v2) only the gentle level; her name ('Friday:' / German 'Flora:') on the first line, her speech blip, and she comes out of Nigel's bag and goes back afterwards.
Options > Quality of Life > Friday Hints On / Off (id 45, last row, default OFF since release v1.5.0 = experimental, user 2026-10-31; ~/.landstalker_friday, env LANDSTALKER_FRIDAY=0|1 wins).  Without a Select press nothing
changes (the game never reads Mode: bit exact).
How: the wrapper of ProcessActionButton $0066AC (once per map pass, like Quick Items / Quick Equip) takes the Mode press edge from the MD pad word (so recordings and input
scripts carry it), when no script runs (g_PlaybackLock $FF12DE = 0) and Nigel lives ($FF543E != 0).  The situation: GetFlagProgress $025318 (the game's own story stage,
used for the villagers' progress-dependent talk) fills g_GameFlagProgress $FF1906 / 07 / 08 (main stage 0..31 + two sub lists; the stored maximum $FF190E.. is taken into
account like HandleProgressDependentDialogue does), plus story flags $FF1000, inventory nibbles $FF1040 and the room g_RmNum1 $FF1204.  The hint table is OUR text in
lang/friday_hints.json (docs/FRIDAY_HINTS.md), compiled here into word streams (glyph code / ~handler word, tools/langbuild.py tokens): the LAST entry whose conditions hold wins.
Display = the chest message sequence of CheckOpenChest: j_SetUpTextbox $022EE8, j_PrintString $022E90 (string id $16 as a carrier; the text layer's InitCompString wrapper
takes our stream instead, tools/patch_lang.py lk_lg_cur), j_SetUpTextDisplay $022EA0.  Test aid: LANDSTALKER_FRIDAY_LOG=1 prints stage / entry / level per press.
Needs patch_lang.py (func_table.c, text layer) and patch_options.py before it.  Idempotent.  usage: patch_friday.py path/to/genrecomp"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langbuild as lb

root = sys.argv[1]
VER = "LK_FRIDAY v2"   # v2: gentle level only, name line, Friday's blip, she flies out of the bag
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("LANDSTALKER_FRIDAY_JSON") or os.path.join(HERE, "..", "lang", "friday_hints.json")   # env: a test copy (build time)

NAME = {"en": "Friday:", "de": "Flora:"}   # her name in the US / German game (user 2026-10-31: 'Friday: bzw. Flora: in der Textbox')
WIDTH = 32   # characters per text box line: the game wraps by itself at ~33-34, in the middle of a word (measured 2026-10-31), so we wrap at word ends first
def wrap(text):
    """free text ('|' = forced line break) -> lines of at most WIDTH characters, broken at spaces"""
    lines = []
    for part in text.split("|"):
        cur = ""
        for w in part.split():
            if cur and len(cur) + 1 + len(w) > WIDTH: lines.append(cur); cur = w
            else: cur = (cur + " " + w) if cur else w
        lines.append(cur)
    return lines
def words(text, lang=None):
    """our hint text -> word list (glyph codes, ~handler words).  Her name leads the first line ('Flora: ...', like the early version of the game wrote speakers);
    the box shows 3 lines and scrolls like a normal dialogue; after every 3 lines the game waits for a button (ContinuePrompt, the arrow); the text ends with
    ContinuePrompt like the chest messages"""
    lines = wrap((NAME[lang] + " " + text) if lang else text)
    out = []
    for i, line in enumerate(lines):
        if i:
            if i % 3 == 0: out.append(~lb.HANDLER[12] & 0xFFFF)   # page full: wait for a button first
            out.append(~lb.HANDLER[1] & 0xFFFF)                    # SoftNewLine
        for t, v in lb.tokens(line):
            if t == "g": out.append(v)
            elif t == "c": out.append(~lb.HANDLER[v] & 0xFFFF)
            else: raise ValueError("no name codes in hints: %r" % text)
    out.append(~lb.HANDLER[12] & 0xFFFF)                           # ContinuePrompt (the chest messages end with it)
    return out

COND = {"stage>=": 1, "sub2>=": 2, "sub3>=": 3, "flag:": 4, "!flag:": 5, "item:": 6, "!item:": 7, "room:": 8}
def cond(c):
    c = c.replace(" ", "")
    for pre in sorted(COND, key=len, reverse=True):
        if c.startswith(pre):
            arg = c[len(pre):]; k = COND[pre]
            if k <= 3: return (k, int(arg), 0)
            if k in (4, 5): b, bit = arg.split("."); return (k, int(b, 16), int(bit))
            if k in (6, 7): return (k, int(arg, 16), 0)
            a, _, b = arg.partition("-"); return (k, int(a), int(b or a))
    raise ValueError("unknown condition %r" % c)

hints = json.load(open(SRC))["hints"] if os.path.exists(SRC) else [{"id": "placeholder", "when": [], "en": ["Hmm...|Let me think.", "Hmm...|Let me think."], "de": ["Hmm...|Lass mich nachdenken.", "Hmm...|Lass mich nachdenken."]}]
data, ents, conds, ids = [], [], [], []
for h in hints:
    c0 = len(conds)
    for c in h.get("when", []): conds.append(cond(c))
    offs = []
    for lang in ("en", "de"):
        for lv in (0, 1):
            w = words(h[lang][lv], lang); offs.append((len(data), len(w))); data.extend(w)
    ents.append((c0, len(conds) - c0, offs)); ids.append(h["id"])
c_words = ",".join("0x%02X,0x%02X" % (w >> 8, w & 0xFF) for w in data)
c_conds = ",".join("{%d,%d,%d}" % c for c in conds) or "{0,0,0}"
c_ents = ",".join("{%d,%d,{%s}}" % (c0, n, ",".join("{%d,%d}" % o for o in offs)) for c0, n, offs in ents)
c_ids = ",".join('"%s"' % re.sub(r"[^A-Za-z0-9_]", "", i) for i in ids)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "typedef struct { uint16_t id; uint16_t n; const uint8_t *w; } LkLgStr;\n"
    assert s.count(a) == 1, "func_table.c: run patch_lang.py first"
    s = s.replace(a, a + "static const LkLgStr *lk_fh_force;   /* " + VER + ": the next InitCompString shows this stream (Friday Hints, tools/patch_friday.py) */\n", 1)
    a = "    lk_lg_cur = r; lk_lg_pos = 0; lk_lg_ext = 0;\n"
    assert s.count(a) == 1
    s = s.replace(a, "    if (lk_fh_force) { r = (LkLgStr *)lk_fh_force; lk_fh_force = NULL; }   /* " + VER + " */\n" + a, 1)
    a = "static void lk_lang_install(void) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_FRIDAY v2: Friday Hints (tools/patch_friday.py, texts lang/friday_hints.json) ---- */
static const uint8_t lk_fh_w[] = { @WORDS@ };
static const struct { uint8_t k; uint16_t a, b; } lk_fh_c[] = { @CONDS@ };
static const struct { uint16_t c0, nc; struct { uint16_t off, n; } t[4]; } lk_fh_e[] = { @ENTS@ };   /* t: en L1, en L2, de L1, de L2 */
static const char *lk_fh_id[] = { @IDS@ };
static int lk_fh_o = -1;
int lk_fh_get(void) { if (lk_fh_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_FRIDAY"); char p[512]; FILE *f; int v = 0; snprintf(p, sizeof p, "%s/.landstalker_friday", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); lk_fh_o = v ? 1 : 0; } return lk_fh_o; }
void lk_fh_set(int v) { const char *h = getenv("HOME"); char p[512]; FILE *f; lk_fh_get(); lk_fh_o = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_friday", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_fh_o); fclose(f); } }
static gen_func_t lk_o_pab_fh;
static int lk_fh_stage[4];   /* [1] main story stage, [2] / [3] sub lists */
static int lk_fh_test(int i) {
    int k = lk_fh_c[i].k, a = lk_fh_c[i].a, b = lk_fh_c[i].b;
    switch (k) {
    case 1: case 2: case 3: return lk_fh_stage[k] >= a;
    case 4: case 5: { int on = (bus_read8(0xFF1000u + (uint32_t)a) >> b) & 1; return k == 4 ? on : !on; }
    case 6: case 7: { uint8_t q = bus_read8(0xFF1040u + (uint32_t)(a >> 1)); int n = (a & 1) ? q >> 4 : q & 15; return k == 6 ? n > 0 : n == 0; }
    case 8: { int r = (int)bus_read16(0xFF1204u); return r >= a && r <= b; }
    }
    return 0;
}
static void lk_fh_ask(void) {
    int e, i, n = (int)(sizeof lk_fh_e / sizeof lk_fh_e[0]), pick = 0, lv, de; static LkLgStr str;
    M68kContext sv = g_m68k;
    lk_call(0x025318u);   /* GetFlagProgress: $FF1906..08 */
    for (i = 1; i <= 3; i++) { int v = bus_read8(0xFF1905u + (uint32_t)i), m = bus_read8(0xFF190Du + (uint32_t)i); lk_fh_stage[i] = v > m ? v : m; }   /* the stored maximum counts too (HandleProgressDependentDialogue) */
    for (e = 0; e < n; e++) { int ok = 1; for (i = 0; i < lk_fh_e[e].nc && ok; i++) ok = lk_fh_test(lk_fh_e[e].c0 + i); if (ok) pick = e; }
    lv = 0;   /* only the gentle level (user 2026-10-31: 'nur die vagen Hinweise, nicht mehr 2-stufig'; the clear level stays in lang/friday_hints.json) */
    de = lk_lg_sel > 0 && !strcmp(lk_lg_codes[lk_lg_sel], "de");
    str.id = 0x16; str.n = lk_fh_e[pick].t[de * 2 + lv].n; str.w = lk_fh_w + 2 * lk_fh_e[pick].t[de * 2 + lv].off;
    if (getenv("LANDSTALKER_FRIDAY_LOG")) fprintf(stderr, "friday: frame %ld stage %d/%d/%d room %d -> %s level %d\n", (long)platform_frame_number(), lk_fh_stage[1], lk_fh_stage[2], lk_fh_stage[3], (int)bus_read16(0xFF1204u), lk_fh_id[pick], lv + 1);
    g_m68k = sv;
    { uint8_t sfx = bus_read8(0xFF1154u);   /* g_TalkSoundEffect: Friday's speech blip while she talks (SetSpecialCharacter $02912C: SpecialCharacterSfxList $02913E, entry 1 = Friday) */
      bus_write8(0xFF1154u, bus_read8(0x02913Fu));
      bus_write8(0xFF114Bu, 0x01); bus_write8(0xFF114Du, 0x11);   /* g_FridayAnimState 1 = out of Nigel's bag, next $11 = hover beside him (what the cutscene actions do, e.g. CSA_0011) */
      lk_call(0x022EE8u);   /* j_SetUpTextbox */
      lk_fh_force = &str; g_m68k.d[0] = 0x16; lk_call(0x022E90u); lk_fh_force = NULL;   /* j_PrintString (carrier id $16); UpdateFridayAnimation runs in every WaitUntilVBlank meanwhile */
      lk_call(0x022EA0u);   /* j_SetUpTextDisplay */
      bus_write8(0xFF114Du, 0x31);   /* next state $31 = back into the bag (the cutscene actions do the same after the dialogue) */
      bus_write8(0xFF1154u, sfx); }
    g_m68k = sv;
}
static void lk_h_pab_fh(void) {
    static uint16_t prev; uint16_t pad = recomp_input_read_pad(0), ed = (uint16_t)(pad & ~prev);
    prev = pad;
    if ((ed & GEN_BTN_MODE) && lk_fh_get() && bus_read16(0xFF12DEu) == 0 && bus_read16(0xFF543Eu) != 0) lk_fh_ask();
    lk_o_pab_fh();
}
static void lk_fh_install(void) {   /* runs at every init pass: only once, a second wrap would make the wrapper call itself (endless loop, 2026-10-31) */
    static int done;
    if (done) return;
    done = 1;
    lk_o_pab_fh = func_table_lookup(0x0066AC);
    if (lk_o_pab_fh) func_table_register(0x0066AC, lk_h_pab_fh); else fprintf(stderr, "friday: ProcessActionButton not found\n");
}
'''
    module = module.replace("@WORDS@", c_words).replace("@CONDS@", c_conds).replace("@ENTS@", c_ents).replace("@IDS@", c_ids)
    s = s.replace(a, module + a, 1)
    h = "        lk_lang_install();   /* LK_LANG v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_fh_install();   /* " + VER + " */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched: %s (%d hints, %d words)" % (VER, len(ents), len(data)))
