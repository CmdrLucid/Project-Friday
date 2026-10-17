#!/usr/bin/env python3
"""Optional 'Buy Quantity' (2026-10-17, user wish after a recording in the Mercator item shop: Eke Eke had to be bought one by one; Options > Gameplay > Buy Quantity Off / On, default Off).
Original: HandleShopInteraction ($024F0A) = price text, yes / no (XS_0042_0), RemoveGold (price of ONE item, d1 -> d0) and GetItem (item id in d2) once.
On: the wrapper of j_RemoveGold ($0177F2) looks at its caller (return address $024F32 = the call in HandleShopInteraction).  After the player said Yes it asks how many:
the limit is min(room left in the inventory = GetRemainingItemAllowedCount $029232, gold / price, 9); with a limit below 2 or for Lifestock (item $3E) nothing changes.  The question is an
on-screen line (OSD, 'HOW MANY? n = 45G') while the wrapper loops WaitUntilVBlank ($000272) + UpdateControllerInputs ($00033E) on the game's controller byte $FF0F8E: UP / RIGHT more, DOWN / LEFT
fewer, A / C buy, B buy one.  Then RemoveGold takes price * n at once (a failure keeps the game's own 'not enough gold' path) and GetItem ($0291D6) runs n - 1 more times (the caller adds the last one).
File ~/.landstalker_buyqty, env LANDSTALKER_BUYQTY=0|1 wins (tests; LANDSTALKER_BUYQTY_PICK="3" answers the question without a pad, LANDSTALKER_BUYQTY_DEBUG=1 prints).
Needs patch_options.py and patch_iteminfo.py before it (insert order).  Idempotent.
usage: patch_buyqty.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_BUYQTY v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_BUYQTY v1: choose how many consumables to buy (tools/patch_buyqty.py) ---- */
static int lk_bq_v = -1;   /* Options > Gameplay > Buy Quantity Off / On, default Off; file ~/.landstalker_buyqty, env LANDSTALKER_BUYQTY=0|1 wins */
int lk_bq_get(void) {
    if (lk_bq_v < 0) { char p[512]; FILE *f; const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_BUYQTY"); int v = 0; snprintf(p, sizeof p, "%s/.landstalker_buyqty", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e) v = atoi(e); lk_bq_v = v ? 1 : 0; }
    return lk_bq_v;
}
void lk_bq_set(int v) { char p[512]; FILE *f; const char *h = getenv("HOME"); lk_bq_get(); lk_bq_v = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_buyqty", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_bq_v); fclose(f); } }
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_ii_install" in s, "func_table.c: run patch_iteminfo.py first"
    module = r'''/* ---- LK_BUYQTY v1: choose how many consumables to buy (tools/patch_buyqty.py) ---- */
extern int lk_bq_get(void);
extern void lk_osd_say(const char *t);
static gen_func_t lk_o_remgold;
static int lk_bq_ask(int item, int price, int max) {   /* the question: returns 1..max */
    const char *pick = getenv("LANDSTALKER_BUYQTY_PICK");
    M68kContext sv = g_m68k;
    int n = 1, first = 1; uint8_t prev = 0;
    if (pick) { n = atoi(pick); if (n < 1) n = 1; if (n > max) n = max; return n; }
    for (;;) {
        uint8_t cur, ed; char t[40];
        snprintf(t, sizeof t, "^HOW MANY? %d = %dG  A:OK", n, n * price); lk_osd_say(t);
        lk_call(0x000272u);   /* WaitUntilVBlank */
        lk_call(0x00033Eu);   /* UpdateControllerInputs */
        cur = bus_read8(0xFF0F8Eu);
        if (first) { first = 0; prev = cur; continue; }   /* the press that said Yes may still be held */
        ed = (uint8_t)(cur & ~prev); prev = cur;
        if (ed & 0x09) { if (n < max) { n++; lk_snd(0x00FA9Eu); } }   /* UP / RIGHT */
        if (ed & 0x06) { if (n > 1) { n--; lk_snd(0x00FA9Eu); } }     /* DOWN / LEFT */
        if (ed & 0x60) { lk_snd(0x00FA54u); break; }                   /* A / C */
        if (ed & 0x10) { n = 1; lk_snd(0x00FA54u); break; }            /* B: just one */
    }
    g_m68k = sv; (void)item;
    return n;
}
static void lk_h_remgold(void) {   /* RemoveGold $0177F2 (reached through the thunk j_RemoveGold $01032C, which tail-calls it): only the call inside HandleShopInteraction ($024F2C, return $024F32) is touched */
    if (getenv("LANDSTALKER_BUYQTY_DEBUG")) fprintf(stderr, "buyqty: RemoveGold on=%d ret=$%06X\n", lk_bq_get(), bus_read32(g_m68k.a[7]));
    if (lk_bq_get() && bus_read32(g_m68k.a[7]) == 0x024F32u) {
        uint32_t item = g_m68k.d[2] & 0xFFu, price = g_m68k.d[0] & 0xFFFFu; int rem, max, gold, n;
        M68kContext sv = g_m68k;
        g_m68k.d[0] = item; lk_call(0x029232u);   /* GetRemainingItemAllowedCount: d1 = max - owned */
        rem = (int16_t)(g_m68k.d[1] & 0xFFFFu);
        g_m68k = sv;
        gold = bus_read16(0xFF120Eu);
        max = rem; if (price && gold / (int)price < max) max = gold / (int)price; if (max > 9) max = 9;
        if (getenv("LANDSTALKER_BUYQTY_DEBUG")) fprintf(stderr, "buyqty: item $%02X price %u gold %d room %d -> max %d\n", item, price, gold, rem, max);
        if (item != 0x3Eu && price && max >= 2) {
            n = lk_bq_ask((int)item, (int)price, max);
            g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | (price * (uint32_t)n);
            if (getenv("LANDSTALKER_BUYQTY_DEBUG")) fprintf(stderr, "buyqty: before d0=%08X gold %d sp=%08X\n", g_m68k.d[0], bus_read16(0xFF120Eu), g_m68k.a[7]);
            lk_o_remgold();
            if (getenv("LANDSTALKER_BUYQTY_DEBUG")) fprintf(stderr, "buyqty: after gold %d sp=%08X\n", bus_read16(0xFF120Eu), g_m68k.a[7]);
            if (!g_m68k.flag_C && n > 1) {   /* paid: the caller adds the last item itself */
                M68kContext r = g_m68k; int i;
                for (i = 1; i < n; i++) { g_m68k.d[0] = item; lk_call(0x0291D6u); }   /* GetItem */
                g_m68k = r;
            }
            if (getenv("LANDSTALKER_BUYQTY_DEBUG")) fprintf(stderr, "buyqty: bought %d, gold now %d, carry %d\n", n, bus_read16(0xFF120Eu), g_m68k.flag_C);
            return;
        }
    }
    lk_o_remgold();
}
static void lk_bq_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_remgold = func_table_lookup(0x0177F2);
    if (lk_o_remgold) func_table_register(0x0177F2, lk_h_remgold); else fprintf(stderr, "buyqty: j_RemoveGold not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_ii_install();   /* LK_ITEMINFO v2 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_bq_install();   /* LK_BUYQTY v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
