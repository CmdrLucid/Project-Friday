#!/usr/bin/env python3
"""genrecomp: write the --ram-dump snapshots of the RECOMPILED build at the end of each frame (scanline wrap), like genrecomp_ref does.

Without this the recompiled build dumped inside the VBlank callback (line 224, right after the VInt handler) while the reference core dumps after
system_frame_gen() (end of the frame), so every comparison differed by ~38 lines of main-thread work and a frame counter. Idempotent.
usage: patch_dumpwrap.py path/to/genrecomp   (run after patch_timing.py / the bus.c patches)
"""
import os, sys
root = sys.argv[1]

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_DUMPWRAP" not in s:
    old = "    if (s_ram_dir && s_frame_no % s_ram_every == 0) {\n        char path[600];\n        snprintf(path, sizeof(path), \"%s/ram_%06ld.bin\", s_ram_dir, s_frame_no);"
    assert s.count(old) == 1, "platform_sdl.c: dump block changed"
    s = s.replace(old, "    if (!lk_dump_external && s_ram_dir && s_frame_no % s_ram_every == 0) {   /* LANDSTALKER_DUMPWRAP */\n        char path[600];\n        snprintf(path, sizeof(path), \"%s/ram_%06ld.bin\", s_ram_dir, s_frame_no);", 1)
    old = "void platform_present_frame(const uint8_t *framebuffer) {\n"
    assert old in s
    helper = '''/* LANDSTALKER_DUMPWRAP: the recompiled build calls this at the end of every frame (bus.c scanline wrap) */
static int lk_dump_external;
void platform_dump_frame_end(long n) {
    lk_dump_external = 1;
    if (s_ram_dir && n % s_ram_every == 0) {
        char path[600];
        snprintf(path, sizeof(path), "%s/ram_%06ld.bin", s_ram_dir, n);
        FILE *f = fopen(path, "wb");
        if (f) { bus_dump_state(f); fclose(f); }
    }
}

'''
    # the helper must be visible before platform_present_frame; the ASCII patch inserts code right after that line, so put it above
    s = s.replace(old, helper + old, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched: LANDSTALKER_DUMPWRAP")

p = os.path.join(root, "src/bus.c")
b = open(p).read()
if "platform_dump_frame_end" not in b:
    old = "            input_end_frame(mcycles_vdp);\n"
    assert b.count(old) == 1, "bus.c: frame wrap layout changed"
    b = b.replace(old, "            { extern void platform_dump_frame_end(long); static long wraps; platform_dump_frame_end(wraps++); }   /* LANDSTALKER_DUMPWRAP */\n" + old, 1)
    open(p, "w").write(b)
    print("bus.c patched: LANDSTALKER_DUMPWRAP")

# input is applied at the START of each frame in the reference (recomp_input_update() before system_frame_gen); the recompiled build applied it in the VBlank callback
# (line 224), one frame later for code that reads the pad in the main thread. Apply it at the frame wrap too, so ref and rec see the same pad state.
b = open(p2 := os.path.join(root, "src/bus.c")).read()
if "LANDSTALKER_WRAPINPUT" not in b:
    old = "            input_end_frame(mcycles_vdp);\n"
    assert b.count(old) == 1, "bus.c: frame wrap layout changed (input)"
    b = b.replace(old, "            { extern void recomp_input_update(void); recomp_input_update(); }   /* LANDSTALKER_WRAPINPUT: pad state for the next frame, like the reference */\n" + old, 1)
    open(p2, "w").write(b)
    print("bus.c patched: LANDSTALKER_WRAPINPUT")

# GENRECOMP_DUMPRANGE=from:to restricts --ram-dump to those frames (per-frame dumps of a long replay would be gigabytes)
q = os.path.join(root, "src/platform_sdl.c")
t = open(q).read()
if "LANDSTALKER_DUMPRANGE" not in t:
    helper = '''/* LANDSTALKER_DUMPRANGE */
static int lk_dump_in_range(long n) {
    static long lo = -2, hi = 0;
    if (lo == -2) { const char *e = getenv("GENRECOMP_DUMPRANGE"); lo = -1; hi = 0x7fffffff; if (e) { lo = atol(e); const char *c = strchr(e, ':'); if (c) hi = atol(c + 1); } }
    return lo < 0 || (n >= lo && n <= hi);
}
'''
    old = "/* LANDSTALKER_DUMPWRAP: the recompiled build calls this"
    assert t.count(old) == 1
    t = t.replace(old, helper + old, 1)
    a = "if (!lk_dump_external && s_ram_dir && s_frame_no % s_ram_every == 0) {"
    assert t.count(a) == 1
    t = t.replace(a, "if (!lk_dump_external && s_ram_dir && s_frame_no % s_ram_every == 0 && lk_dump_in_range(s_frame_no)) {", 1)
    b = "if (s_ram_dir && n % s_ram_every == 0) {"
    assert t.count(b) == 1
    t = t.replace(b, "if (s_ram_dir && n % s_ram_every == 0 && lk_dump_in_range(n)) {", 1)
    open(q, "w").write(t)
    print("platform_sdl.c patched: LANDSTALKER_DUMPRANGE")
