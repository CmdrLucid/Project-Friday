#!/usr/bin/env python3
"""Project-Friday launcher: asks for YOUR Landstalker ROM, builds the game from it on the first start (progress
window), then starts it. Nothing ROM-derived is part of the release; everything is generated into the user's data
folder and is tied to the ROM's SHA-1. The ROM must be present at EVERY start (it is checked each time).

  python3 firstrun.py [--rom FILE] [--rebuild] [--cc "zig cc"] [--no-gui] [--build-only] [-- game args]

Environment: LANDSTALKER_ROM, LANDSTALKER_DATA (data folder), SDL2_CFLAGS / SDL2_LIBS, CC.
Folder layout next to this file (release):  tools/ docs/symbols.json recomp.json src/main.c vendor/genrecomp/
                                            vendor/zig/zig (optional, else a system compiler is used)
"""
import hashlib, json, os, re, shlex, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WIN = os.name == "nt"
os.environ.setdefault("PYTHONUTF8", "1")      # the patch tools read / write UTF-8 sources (the Windows default would be cp1252)


def q(path):
    """quote a path for a command string that shlex.split(posix) parses later (forward slashes also work on Windows)"""
    return '"%s"' % path.replace("\\", "/") if WIN else shlex.quote(path)


def rmtree(path):
    def onerr(fn, p, exc):          # read-only files on Windows
        try:
            os.chmod(p, 0o700)
            fn(p)
        except OSError:
            pass
    shutil.rmtree(path, onerror=onerr)
NAME = "Project-Friday"
# SHA-1 of the ROM version this project is built and tested for (2 MB Genesis dump, as used on the Steam Deck)
KNOWN_ROMS = {"24345e29427b000b90df778965dd8834300a9dde": "Landstalker (Mega Drive)"}
DATA = os.environ.get("LANDSTALKER_DATA") or (
    os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local"), "Project-Friday") if WIN else
    os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"), "project-friday"))
CONFIG = os.path.join(DATA, "config.json")
NOTICE = ("Project-Friday builds the game on your computer from your own Landstalker ROM.\n"
          "The built game is derived from that ROM: do not give it (or the ROM) to anyone else.")


# ---------------------------------------------------------------- user interface (zenity / console)
class Ui:
    def __init__(self, gui):
        if WIN:   # dialogs through PowerShell + Windows Forms (present on every Windows 10 / 11), progress as text in the console window
            self.gui = gui and bool(shutil.which("powershell"))
        else:
            self.gui = gui and bool(shutil.which("zenity")) and bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        self.proc = None
        self.t0 = time.time()

    def _ps(self, script, **env):
        e = dict(os.environ, **env)
        return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-Command",
                               "Add-Type -AssemblyName System.Windows.Forms; " + script], capture_output=True, text=True, env=e)

    def _box(self, text, icon):
        if WIN:
            self._ps("[void][System.Windows.Forms.MessageBox]::Show($env:PF_MSG, 'Project-Friday', 'OK', '%s')" % icon, PF_MSG=text)
        else:
            subprocess.run(["zenity", "--error" if icon == "Error" else "--info", "--no-markup", "--width=480", "--title=" + NAME, "--text=" + text])

    def say(self, text):
        print(text, flush=True)

    def error(self, text):
        print("ERROR: " + text, file=sys.stderr, flush=True)
        if self.gui:
            self._box(text, "Error")

    def info(self, text):
        print(text, flush=True)
        if self.gui:
            self._box(text, "Information")

    def ask_rom(self, why):
        self.say(why)
        if self.gui and WIN:
            r = self._ps("$f = New-Object System.Windows.Forms.OpenFileDialog; $f.Title = 'Select your Landstalker ROM (.md / .bin / .gen)'; "
                         "$f.Filter = 'Mega Drive ROM (*.md;*.bin;*.gen)|*.md;*.bin;*.gen|All files (*.*)|*.*'; "
                         "if ($f.ShowDialog() -eq 'OK') { [Console]::Out.Write($f.FileName) }")
            return r.stdout.strip() or None
        if self.gui:
            r = subprocess.run(["zenity", "--file-selection", "--title=Select your Landstalker ROM (.md / .bin / .gen)"],
                               capture_output=True, text=True)
            return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
        try:
            return input("Path to your Landstalker ROM: ").strip() or None
        except EOFError:
            return None

    def progress_open(self, title):
        if self.gui and not WIN:
            self.proc = subprocess.Popen(
                ["zenity", "--progress", "--no-markup", "--width=480", "--title=" + NAME, "--text=" + title,
                 "--percentage=0", "--auto-close"], stdin=subprocess.PIPE, text=True)

    def progress(self, pct, text):
        pct = max(0, min(100, int(pct)))
        line = "%3d%%  %s" % (pct, text)
        if self.proc:
            try:
                self.proc.stdin.write("%d\n# %s\n" % (pct, text))
                self.proc.stdin.flush()
            except (BrokenPipeError, ValueError):
                raise Cancelled()
            if self.proc.poll() is not None:
                raise Cancelled()
        else:
            print("\r" + line[:100].ljust(100), end="" if pct < 100 else "\n", flush=True)

    def progress_close(self):
        if self.proc:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            self.proc.wait()
            self.proc = None


class Cancelled(Exception):
    pass


# ---------------------------------------------------------------- helpers
def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config():
    try:
        return json.load(open(CONFIG))
    except Exception:
        return {}


def save_config(cfg):
    os.makedirs(DATA, exist_ok=True)
    json.dump(cfg, open(CONFIG, "w"), indent=1)


def check_rom(path):
    """-> (sha1, None) or (None, reason)"""
    if not path or not os.path.isfile(path):
        return None, "File not found: %s" % path
    size = os.path.getsize(path)
    if size != 2 * 1024 * 1024:
        return None, "This is not the expected ROM (size %d bytes, expected 2097152). Raw .md / .bin / .gen dumps only; .smd or zip files must be converted / unpacked first." % size
    h = sha1(path)
    if h not in KNOWN_ROMS:
        return None, "This ROM is not the version Project-Friday supports (SHA-1 %s)." % h
    return h, None


def find_rom(ui, args, cfg):
    cands = [args.rom, os.environ.get("LANDSTALKER_ROM"), cfg.get("rom")]
    for c in cands:
        if c:
            h, why = check_rom(c)
            if h:
                if cfg.get("rom") != os.path.abspath(c):
                    cfg["rom"] = os.path.abspath(c)
                    save_config(cfg)
                return c, h
            ui.say("ROM %s: %s" % (c, why))
            if c == args.rom:
                ui.error(why)
                return None, None
    why = "Please select your Landstalker ROM file."
    for _ in range(3):
        p = ui.ask_rom(why)
        if not p:
            return None, None
        h, why2 = check_rom(p)
        if h:
            cfg["rom"] = os.path.abspath(p)
            save_config(cfg)
            return p, h
        ui.error(why2)
        why = "Please select the correct ROM file."
    return None, None


def build_id(rom_sha):
    """Changes whenever the build inputs change (patches, symbols, seeds, genrecomp revision, ROM)."""
    h = hashlib.sha1(rom_sha.encode())
    files = [os.path.join(HERE, "recomp.json"), os.path.join(HERE, "docs", "symbols.json"), os.path.join(HERE, "src", "main.c"),
             os.path.join(HERE, "build.sh"), os.path.join(HERE, "vendor", "genrecomp", "VENDOR_REVISION.txt")]
    files += sorted(os.path.join(HERE, "tools", f) for f in os.listdir(os.path.join(HERE, "tools")) if f.endswith((".py", ".c", ".h", ".json")))
    for f in files:
        if os.path.isfile(f):
            h.update(os.path.basename(f).encode())
            h.update(open(f, "rb").read())
    return h.hexdigest()[:12]


def pick_compiler(args):
    if args.cc:
        return args.cc
    if os.environ.get("CC"):
        return os.environ["CC"]
    z = os.path.join(HERE, "vendor", "zig", "zig.exe" if WIN else "zig")
    if os.path.isfile(z):
        return q(z) + " cc" + (" -target x86_64-windows-gnu" if WIN else "")
    if shutil.which("zig"):
        return "zig cc" + (" -target x86_64-windows-gnu" if WIN else "")
    for c in ("cc", "gcc", "clang"):
        if shutil.which(c):
            return c
    return None


def sdl_flags():
    """-> (cflags, libs) for SDL2: env first, then the headers shipped in vendor/sdl2 + the system's libSDL2-2.0.so.0
    (the dev package with the libSDL2.so symlink is usually missing on user machines), then sdl2-config."""
    if os.environ.get("SDL2_CFLAGS") is not None and os.environ.get("SDL2_LIBS") is not None:
        return os.environ["SDL2_CFLAGS"], os.environ["SDL2_LIBS"]
    inc = os.path.join(HERE, "vendor", "sdl2", "include", "SDL2")
    if WIN:   # MinGW development package of SDL2 (include/SDL2, lib/libSDL2main.a + libSDL2.dll.a, bin/SDL2.dll is copied next to the game)
        if not os.path.isdir(inc):
            raise RuntimeError("vendor/sdl2 is missing in this package")
        ld = os.path.join(HERE, "vendor", "sdl2", "lib")
        return ("-I%s -Dmain=SDL_main" % q(inc),
                "-L%s -lmingw32 %s %s -lm" % (q(ld), q(os.path.join(ld, "libSDL2main.a")), q(os.path.join(ld, "libSDL2.dll.a"))))
    lib = None
    if os.path.isdir(inc):
        try:
            out = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True).stdout
            m = re.search(r"libSDL2-2\.0\.so\.0 .*=> (\S+)", out)
            lib = m.group(1) if m else None
        except OSError:
            pass
        if not lib:
            for d in ("/usr/lib", "/usr/lib64", "/usr/lib/x86_64-linux-gnu", "/lib64", "/lib/x86_64-linux-gnu"):
                if os.path.exists(os.path.join(d, "libSDL2-2.0.so.0")):
                    lib = os.path.join(d, "libSDL2-2.0.so.0")
                    break
        if lib:
            # the parent directory too: SDL_config.h of Debian / Ubuntu includes <SDL2/_real_SDL_config.h>
            return "-I%s -I%s -D_GNU_SOURCE=1 -D_REENTRANT" % (shlex.quote(inc), shlex.quote(os.path.dirname(inc))), shlex.quote(lib)
    if shutil.which("sdl2-config"):
        c = subprocess.check_output(["sdl2-config", "--cflags"], text=True).strip()
        l = subprocess.check_output(["sdl2-config", "--libs"], text=True).strip()
        return c, l
    raise RuntimeError("SDL2 not found: install the SDL2 runtime library (libSDL2-2.0.so.0).")


def patch_steps():
    """The patch / generate commands, read from build.sh so there is ONE list (lines `python3 tools/X args`)."""
    steps = []
    for line in open(os.path.join(HERE, "build.sh"), encoding="utf-8"):
        m = re.match(r'^python3 (tools/\S+\.py)(.*)$', line.rstrip("\n"))
        if not m:
            continue
        rest = re.split(r"\s+(\|\||\|)\s", m.group(2))[0]          # drop `|| echo ...` / `| head`
        script = m.group(1)
        if script in ("tools/symbolize.py", "tools/check_splits.py"):
            continue                                                  # optional diagnostics
        steps.append([script] + shlex.split(rest))
    return steps


# ---------------------------------------------------------------- the build
def build(ui, rom, rom_sha, bid, cc):
    work = os.path.join(DATA, "builds", bid + "-" + rom_sha[:8])
    exe = os.path.join(work, "out", "landstalker.exe" if os.name == "nt" else "landstalker")
    if os.path.isfile(os.path.join(work, "DONE")) and os.path.isfile(exe):
        return exe
    vendor = os.path.join(HERE, "vendor", "genrecomp")
    if not os.path.isfile(os.path.join(vendor, "CMakeLists.txt")):
        raise RuntimeError("vendor/genrecomp is missing (run tools/make_vendor.py, or use the release package)")
    steps = patch_steps()
    n = len(steps)
    # weights (percent): prepare 3, patch/generate chain 57 (the generate step is the long one), compile 40
    ui.progress_open("Building the game from your ROM (first start only, about 5 to 25 minutes) ...")
    if os.path.isdir(work):
        rmtree(work)
    os.makedirs(work)
    log = open(os.path.join(work, "build.log"), "w")

    def run(cmd, label, cwd=work, env=None):
        log.write("\n$ %s\n" % " ".join(cmd))
        log.flush()
        r = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env)
        if r.returncode:
            log.close()
            tail = open(os.path.join(work, "build.log")).read()[-1500:]
            raise RuntimeError("Step failed: %s\n\n%s\n\nFull log: %s" % (label, tail, os.path.join(work, "build.log")))

    ui.progress(0, "Preparing sources ...")
    for d in ("tools", "docs"):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    for f in sorted(os.listdir(os.path.join(HERE, "tools"))):
        p = os.path.join(HERE, "tools", f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(work, "tools", f))
    for sub in ("funcdiff",):
        pass
    shutil.copy2(os.path.join(HERE, "docs", "symbols.json"), os.path.join(work, "docs", "symbols.json"))
    shutil.copy2(os.path.join(HERE, "recomp.json"), os.path.join(work, "recomp.json"))
    os.makedirs(os.path.join(work, "src", "recomp"))
    shutil.copy2(os.path.join(HERE, "src", "main.c"), os.path.join(work, "src", "main.c"))
    gr = os.path.join(work, ".deps", "genrecomp")
    shutil.copytree(vendor, gr)
    ui.progress(2, "Preparing genrecomp ...")
    # the three in-place edits of build.sh (kept in sync by hand; verified by comparing the generated tree)
    p = os.path.join(gr, "src", "func_table.c")
    s = open(p).read().replace("#define FUNC_TABLE_SIZE  4096", "#define FUNC_TABLE_SIZE  16384")
    open(p, "w").write(s)
    p = os.path.join(gr, "src", "platform_sdl.c")
    s = open(p).read().replace("SDL_PIXELFORMAT_RGBX8888", "SDL_PIXELFORMAT_ARGB8888")
    if "LANDSTALKER_ASCII" not in s:
        m = "void platform_present_frame(const uint8_t *framebuffer) {\n"
        if m not in s:
            raise RuntimeError("platform_sdl.c layout changed")
        s = s.replace(m, m + open(os.path.join(work, "tools", "ascii_patch.c")).read(), 1)
    open(p, "w").write(s)
    try:
        subprocess.run([sys.executable, "-c", "import capstone"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        ui.progress(2, "Installing the python module 'capstone' ...")
        wheels = os.path.join(HERE, "vendor", "wheels")
        cmd = [sys.executable, "-m", "pip", "install", "--user", "--quiet", "capstone"]
        if os.path.isdir(wheels):
            cmd[5:5] = ["--no-index", "--find-links", wheels]
        run(cmd, "install capstone")
    # the patch / generate chain
    for i, st in enumerate(steps):
        args = [rom if a == "$ROM" else a for a in st[1:]]
        label = os.path.basename(st[0])
        ui.progress(3 + 57.0 * i / n, "Step %d of %d: %s" % (i + 1, n, label))
        run([sys.executable, st[0]] + args, label)
    # compile
    env = dict(os.environ)
    env["CC"] = cc
    env["SDL2_CFLAGS"], env["SDL2_LIBS"] = sdl_flags()
    env.setdefault("ZIG_GLOBAL_CACHE_DIR", os.path.join(DATA, "zigcache"))
    ui.progress(60, "Compiling ...")
    cmd = [sys.executable, os.path.join(work, "tools", "zigbuild.py"), "--cc", cc, "--out", os.path.join(work, "out")]
    log.write("\n$ %s\n" % " ".join(cmd))
    log.flush()
    pr = subprocess.Popen(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    for line in pr.stdout:
        log.write(line)
        m = re.match(r"PROGRESS (\d+) (\d+) (\S+)", line)
        if m:
            d, t = int(m.group(1)), max(1, int(m.group(2)))
            ui.progress(60 + 39.0 * d / t, "Compiling %d of %d" % (d, t))
        elif line.startswith("zigbuild: linking"):
            ui.progress(99, "Linking ...")
    if pr.wait() or not os.path.isfile(exe):
        log.close()
        tail = open(os.path.join(work, "build.log")).read()[-1500:]
        raise RuntimeError("Compiling failed.\n\n%s\n\nFull log: %s" % (tail, os.path.join(work, "build.log")))
    log.close()
    if WIN:   # the game needs SDL2.dll next to it
        shutil.copy2(os.path.join(HERE, "vendor", "sdl2", "bin", "SDL2.dll"), os.path.join(work, "out", "SDL2.dll"))
    # the generated sources are no longer needed: keep only the program (saves disk space)
    rmtree(os.path.join(work, "src"))
    rmtree(os.path.join(work, ".deps"))
    rmtree(os.path.join(work, "out", "obj"))
    open(os.path.join(work, "DONE"), "w").write(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    # remove older builds
    bd = os.path.join(DATA, "builds")
    for d in os.listdir(bd):
        if os.path.join(bd, d) != work:
            rmtree(os.path.join(bd, d))
    ui.progress(100, "Done")
    return exe


def selftest(cc):
    """Compile and link a tiny SDL2 program with exactly the compiler and flags the real build uses (no ROM needed)."""
    import tempfile
    if cc is None:
        print("selftest FAILED: no C compiler found")
        return 1
    cflags, libs = sdl_flags()
    d = tempfile.mkdtemp(prefix="pf-selftest-")
    src, exe = os.path.join(d, "t.c"), os.path.join(d, "t.exe" if WIN else "t")
    if WIN and os.path.isfile(os.path.join(HERE, "vendor", "sdl2", "bin", "SDL2.dll")):
        shutil.copy2(os.path.join(HERE, "vendor", "sdl2", "bin", "SDL2.dll"), os.path.join(d, "SDL2.dll"))
    open(src, "w").write('#include <SDL.h>\nint main(void) { return SDL_MAJOR_VERSION == 2 ? 0 : 1; }\n')
    env = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=os.path.join(d, "zigcache"))
    r = subprocess.run(shlex.split(cc) + shlex.split(cflags) + [src] + shlex.split(libs) + ["-o", exe], capture_output=True, text=True, env=env)
    if r.returncode:
        print("selftest FAILED (compile / link):\n" + r.stderr[-1500:])
        return 1
    if subprocess.run([exe]).returncode:
        print("selftest FAILED (run)")
        return 1
    print("selftest ok: compiler '%s', SDL2 headers and library work" % cc)
    rmtree(d)
    return 0


def main():
    argv = sys.argv[1:]
    game_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, game_args = argv[:i], argv[i + 1:]
    import argparse
    ap = argparse.ArgumentParser(description=NAME + " launcher")
    ap.add_argument("--rom")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--cc")
    ap.add_argument("--no-gui", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="check compiler + SDL2 headers / library without a ROM (used by CI)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest(pick_compiler(args))
    ui = Ui(not args.no_gui)
    cfg = load_config()
    if not cfg.get("notice_shown"):
        ui.info(NOTICE)
        cfg["notice_shown"] = True
        save_config(cfg)
    rom, rom_sha = find_rom(ui, args, cfg)
    if not rom:
        return 1
    cc = pick_compiler(args)
    bid = build_id(rom_sha)
    try:
        if args.rebuild:
            rmtree(os.path.join(DATA, "builds"))
        if cc is None and not os.path.isfile(os.path.join(DATA, "builds", bid + "-" + rom_sha[:8], "DONE")):
            ui.error("No C compiler found (the release package brings its own; for a source checkout install gcc or zig).")
            return 1
        exe = build(ui, rom, rom_sha, bid, cc)
    except Cancelled:
        ui.say("Cancelled.")
        return 2
    except Exception as e:
        ui.progress_close()
        ui.error(str(e))
        return 1
    ui.progress_close()
    if args.build_only:
        print("built:", exe)
        return 0
    env = dict(os.environ)
    env.setdefault("HOME", os.path.expanduser("~"))     # the game keeps its settings in ~/.landstalker_* (Windows: the user profile)
    if WIN:
        return subprocess.call([exe] + game_args + [rom], env=env, cwd=os.path.dirname(exe))
    os.execv(exe, [exe] + game_args + [rom])


if __name__ == "__main__":
    sys.exit(main())
