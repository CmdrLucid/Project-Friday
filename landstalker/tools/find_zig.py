#!/usr/bin/env python3
"""find_zig.py: prints the path of the zig compiler the release packages use (pinned version, packaging/make_appimage.py ZIG_VERSION).
Order: vendor/zig/zig (inside a release package), ~/.cache/project-friday-build/zig-<version>/zig (already downloaded), else download it once
(ziglang.org, checksum checked, packaging/make_appimage.get_zig). Used by build.sh (user 2026-11-18: the dev build must use the SAME compiler as
the downloads; GitHub #21 was visible only with zig / clang)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "packaging"))
import make_appimage as m   # noqa: E402
v = os.path.join(ROOT, "vendor", "zig", "zig")
c = os.path.join(m.CACHE, "zig-" + m.ZIG_VERSION, "zig")
if os.path.isfile(v): print(v)
elif os.path.isfile(c): print(c)
else:
    print("find_zig: downloading zig %s once into %s" % (m.ZIG_VERSION, m.CACHE), file=sys.stderr)
    print(os.path.join(m.get_zig(), "zig"))
