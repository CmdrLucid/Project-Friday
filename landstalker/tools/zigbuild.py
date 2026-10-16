#!/usr/bin/env python3
"""Compile + link the game WITHOUT cmake / make (for the release launcher, works with `zig cc`, gcc or clang).

Same sources, defines and flags as CMakeLists.txt + .deps/genrecomp/CMakeLists.txt, only the build driver differs:
  python3 tools/zigbuild.py [--cc "zig cc"] [--out build_zig] [--extra "-fsanitize=undefined -g"] [--jobs N] [--sdl-cflags "..."] [--sdl-libs "..."]

Environment: CC (default: "zig cc" if `zig` is on PATH, else cc), SDL2_CFLAGS / SDL2_LIBS (default: sdl2-config).
Output: <out>/landstalker (objects in <out>/obj, rebuilt only when a source or header is newer).
Progress lines: `PROGRESS done total name` on stdout (the launcher turns them into the progress bar).
"""
import argparse, glob, os, shlex, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GR = os.path.join(ROOT, ".deps", "genrecomp")
GPGX = os.path.join(GR, "ext", "Genesis-Plus-GX", "core")

# keep in sync with .deps/genrecomp/CMakeLists.txt (checked by --check-list)
GPGX_SRC = """genesis system io_ctrl loadrom mem68k membnk memz80 state vdp_ctrl vdp_render
m68k/m68kcpu m68k/s68kcpu z80/z80 sound/blip_buf sound/eq sound/psg sound/sound sound/ym2612 sound/ym2413
sound/ym3438 sound/opll cart_hw/md_cart cart_hw/sms_cart cart_hw/sram cart_hw/eeprom_93c cart_hw/eeprom_i2c
cart_hw/eeprom_spi cart_hw/flash_cfi cart_hw/ggenie cart_hw/areplay cart_hw/megasd cart_hw/yx5200
cart_hw/svp/svp cart_hw/svp/ssp16 input_hw/input input_hw/gamepad input_hw/activator input_hw/graphic_board
input_hw/lightgun input_hw/mouse input_hw/paddle input_hw/smash input_hw/sportspad input_hw/teamplayer
input_hw/terebi_oekaki input_hw/xe_1ap cd_hw/cdc cd_hw/cdd cd_hw/gfx cd_hw/pcm cd_hw/scd cd_hw/cd_cart""".split()
GR_SRC = "genrecomp m68k bus func_table lk_symtab io platform_sdl input".split()
DEFS = ["-DHAVE_NO_SPRITE_LIMIT", "-DLSB_FIRST", "-DUSE_32BPP_RENDERING"]
INC_SUB = ["", "m68k", "z80", "sound", "cart_hw", "cart_hw/svp", "cd_hw", "input_hw", "ntsc", "sound/minimp3"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cc", default=os.environ.get("CC") or ("zig cc" if shutil.which("zig") else "cc"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build_zig"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--sdl-cflags", default=os.environ.get("SDL2_CFLAGS"))
    ap.add_argument("--sdl-libs", default=os.environ.get("SDL2_LIBS"))
    ap.add_argument("--extra", default="", help="extra compile + link flags for every file, e.g. \"-fsanitize=undefined -g\"")
    ap.add_argument("--extra-gpgx", default="", help="additional flags only for the Genesis Plus GX files (e.g. \"-fno-sanitize=shift\" to skip its known benign shifts)")
    ap.add_argument("--no-game", action="store_true", help="compile genrecomp + Genesis Plus GX only (no generated code, no link): environment check")
    ap.add_argument("--check-list", action="store_true", help="only compare the source list with genrecomp's CMakeLists.txt")
    a = ap.parse_args()

    if a.check_list:
        cm = open(os.path.join(GR, "CMakeLists.txt")).read()
        miss = [s for s in GPGX_SRC if "${GPGX_DIR}/%s.c" % s not in cm]
        miss += [s for s in GR_SRC if "src/%s.c" % s not in cm]
        print("source list differs from CMakeLists.txt:" if miss else "source list ok", miss or "")
        return 1 if miss else 0

    cc = shlex.split(a.cc) + shlex.split(a.extra)
    if not os.path.isdir(GPGX):
        sys.exit("genrecomp not found at %s" % GR)
    sdl_c = shlex.split(a.sdl_cflags if a.sdl_cflags is not None else subprocess.check_output(["sdl2-config", "--cflags"], text=True))
    sdl_l = shlex.split(a.sdl_libs if a.sdl_libs is not None else subprocess.check_output(["sdl2-config", "--libs"], text=True))

    inc_gpgx = ["-I" + os.path.join(GPGX, s).rstrip("/") for s in INC_SUB]
    inc_common = ["-I" + os.path.join(GR, "include"), "-I" + os.path.join(GR, "src"), "-I" + os.path.join(ROOT, "src")]
    jobs = []  # (src, obj, flags)
    O = ["-O3", "-DNDEBUG"]
    for s in GPGX_SRC:
        jobs.append((os.path.join(GPGX, s + ".c"), "gpgx_" + s.replace("/", "_"),
                     O + ["-std=gnu17", "-w"] + shlex.split(a.extra_gpgx) + DEFS + inc_gpgx + ["-I" + os.path.join(GR, "include"), "-I" + os.path.join(GR, "src")] + sdl_c))
    jobs.append((os.path.join(GR, "src", "osd.c"), "gpgx_osd",
                 O + ["-std=gnu17", "-w"] + DEFS + inc_gpgx + ["-I" + os.path.join(GR, "include"), "-I" + os.path.join(GR, "src")] + sdl_c))
    for s in GR_SRC:
        jobs.append((os.path.join(GR, "src", s + ".c"), "gr_" + s,
                     O + ["-std=gnu17"] + DEFS + inc_gpgx + inc_common + sdl_c))
    recomp = sorted(glob.glob(os.path.join(ROOT, "src", "recomp", "*.c")))
    if not recomp and not a.no_game:
        sys.exit("src/recomp is empty (generate the code first)")
    if not a.no_game:
        for s in [os.path.join(ROOT, "src", "main.c")] + recomp:
            jobs.append((s, "game_" + os.path.basename(s)[:-2], O + inc_common[:0] + inc_gpgx + inc_common + sdl_c))

    objd = os.path.join(a.out, "obj")
    os.makedirs(objd, exist_ok=True)
    stamp = os.path.join(objd, ".flags")          # compiler / flags changed -> everything is rebuilt
    want = a.cc + "|" + a.extra + "|" + a.extra_gpgx
    if not os.path.exists(stamp) or open(stamp).read() != want:
        for f in glob.glob(os.path.join(objd, "*.o")):
            os.remove(f)
        open(stamp, "w").write(want)
    # newest header decides whether everything is rebuilt (headers are few, the generated sources are many)
    hdrs = glob.glob(os.path.join(GPGX, "**", "*.h"), recursive=True) + glob.glob(os.path.join(GR, "src", "*.h")) \
        + glob.glob(os.path.join(GR, "include", "**", "*.h"), recursive=True) + glob.glob(os.path.join(ROOT, "src", "*.h")) \
        + glob.glob(os.path.join(ROOT, "src", "recomp", "*.h"))
    newest_h = max(os.path.getmtime(h) for h in hdrs)

    todo = []
    objs = []
    for src, name, fl in jobs:
        obj = os.path.join(objd, name + ".o")
        objs.append(obj)
        if not os.path.exists(obj) or os.path.getmtime(obj) < max(os.path.getmtime(src), newest_h):
            todo.append((src, obj, fl))
    total, done, lock, errors = len(todo), [0], threading.Lock(), []
    print("zigbuild: %d of %d files to compile with: %s" % (total, len(jobs), a.cc), flush=True)

    def comp(j):
        src, obj, fl = j
        for attempt in range(4):   # zig's compile cache can fail (seen under Wine: CacheCheckFailed, no file locking): retry, the last time with a private cache
            env = None
            if attempt == 3 and "CacheCheckFailed" in (r.stderr or ""):
                import tempfile
                pc = tempfile.mkdtemp(prefix="zigcache-")
                env = dict(os.environ, ZIG_LOCAL_CACHE_DIR=pc, ZIG_GLOBAL_CACHE_DIR=pc)
            r = subprocess.run(cc + fl + ["-c", src, "-o", obj], capture_output=True, text=True, env=env)
            if env:
                shutil.rmtree(env["ZIG_LOCAL_CACHE_DIR"], ignore_errors=True)
            if r.returncode == 0:
                break
        with lock:
            done[0] += 1
            if r.returncode:
                errors.append((src, r.stderr))
            print("PROGRESS %d %d %s" % (done[0], total, os.path.basename(src)), flush=True)

    if todo and "zig" in a.cc:   # warm-up: one serial compile fills zig's global cache (libc headers, runtime) before the parallel ones start (CacheCheckFailed under Wine)
        import tempfile
        wd = tempfile.mkdtemp(prefix="zigwarm-")
        wsrc = os.path.join(wd, "w.c")
        open(wsrc, "w").write("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <setjmp.h>\n#include <math.h>\nint main(void) { return 0; }\n")
        subprocess.run(cc + O + ["-c", wsrc, "-o", os.path.join(wd, "w.o")], capture_output=True)
        shutil.rmtree(wd, ignore_errors=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(comp, todo))
    if errors:   # second chance: the failed files one by one (no parallel cache races)
        again = [j for j in todo if any(e[0] == j[0] for e in errors)]
        errors.clear()
        done[0] -= len(again)
        for j in again:
            comp(j)
    if errors:
        for s, e in errors[:3]:
            print("ERROR compiling %s:\n%s" % (s, e[-1500:]), file=sys.stderr)
        return 1
    if a.no_game:
        print("zigbuild: compiled %d files (genrecomp + Genesis Plus GX, no game)" % len(jobs), flush=True)
        return 0
    exe = os.path.join(a.out, "landstalker.exe" if "windows" in a.cc else "landstalker")
    print("zigbuild: linking", flush=True)
    r = subprocess.run(cc + ["-O3"] + objs + sdl_l + ["-lm", "-o", exe])
    if r.returncode:
        return 1
    print("zigbuild: built", exe, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
