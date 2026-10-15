#!/usr/bin/env python3
"""genrecomp: persist the cartridge's battery RAM (SRAM) to a file (idempotent).

Landstalker saves via the church book into SRAM ($200001..). genrecomp keeps it only in memory (GPGX sram.sram), so saves vanished when the
program quit. This patch loads `<rom path without extension>.srm` (or $LANDSTALKER_SAVE) after the hard reset, writes it back whenever it
changed (checked every 120 frames) and at shutdown. Prints `genrecomp: SRAM ...` lines.
usage: patch_sram.py path/to/genrecomp
"""
import sys, os
p = os.path.join(sys.argv[1], "src/genrecomp.c")
s = open(p).read()
if "LANDSTALKER_SRAM" in s:
    print("genrecomp.c already patched: LANDSTALKER_SRAM"); sys.exit(0)

def rep(old, new):
    global s
    assert old in s, f"genrecomp.c: layout changed ({old[:50]!r})"
    s = s.replace(old, new, 1)

HELPERS = r'''/* LANDSTALKER_SRAM: battery RAM persistence */
static char s_srm_path[MAXPATHLEN + 8];
static uint8_t s_srm_saved[0x10000];
static int s_srm_frames;

static void lk_sram_flush(void) {
    if (!sram.on || !s_srm_path[0]) return;
    if (memcmp(sram.sram, s_srm_saved, sizeof(s_srm_saved)) == 0) return;
    FILE *f = fopen(s_srm_path, "wb");
    if (!f) { fprintf(stderr, "genrecomp: SRAM: cannot write %s\n", s_srm_path); return; }
    fwrite(sram.sram, 1, sizeof(s_srm_saved), f);
    fclose(f);
    memcpy(s_srm_saved, sram.sram, sizeof(s_srm_saved));
    fprintf(stderr, "genrecomp: SRAM saved to %s\n", s_srm_path);
}

static void lk_sram_load(const char *rom_path) {
    const char *env = getenv("LANDSTALKER_SAVE");
    if (env && *env) {
        snprintf(s_srm_path, sizeof(s_srm_path), "%s", env);
    } else {
        snprintf(s_srm_path, sizeof(s_srm_path), "%s", rom_path);
        char *dot = strrchr(s_srm_path, '.'), *slash = strrchr(s_srm_path, '/');
        if (dot && (!slash || dot > slash)) *dot = 0;
        strncat(s_srm_path, ".srm", 5);
    }
    if (!sram.on) { fprintf(stderr, "genrecomp: SRAM: cartridge reports no battery RAM (saving disabled)\n"); s_srm_path[0] = 0; return; }
    FILE *f = fopen(s_srm_path, "rb");
    if (f) {
        size_t n = fread(sram.sram, 1, sizeof(s_srm_saved), f);
        fclose(f);
        fprintf(stderr, "genrecomp: SRAM loaded from %s (%zu bytes)\n", s_srm_path, n);
    } else {
        fprintf(stderr, "genrecomp: SRAM: new save file will be %s\n", s_srm_path);
    }
    memcpy(s_srm_saved, sram.sram, sizeof(s_srm_saved));
}

'''
rep("bool genrecomp_load_rom(const char *path) {\n", HELPERS + "bool genrecomp_load_rom(const char *path) {\n")
rep("    /* Hard reset everything */\n    system_reset();\n", "    /* Hard reset everything */\n    system_reset();\n    lk_sram_load(path);\n")
rep("void genrecomp_end_frame(void) {\n", "void genrecomp_end_frame(void) {\n    if (++s_srm_frames >= 120) { s_srm_frames = 0; lk_sram_flush(); }\n")
rep("void genrecomp_shutdown(void) {\n    if (!s_initialized) return;\n", "void genrecomp_shutdown(void) {\n    if (!s_initialized) return;\n    lk_sram_flush();\n")
open(p, "w").write(s); print("genrecomp.c patched: LANDSTALKER_SRAM")
