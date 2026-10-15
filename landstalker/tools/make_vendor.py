#!/usr/bin/env python3
"""Export a PRISTINE copy of genrecomp (+ the Genesis Plus GX submodule) from the git checkout in .deps/genrecomp.

  python3 tools/make_vendor.py [OUTDIR]            (default: vendor/genrecomp, ignored by git; source = .deps/genrecomp)
  python3 tools/make_vendor.py --fetch [OUTDIR]    (CI: clone genrecomp at the revision pinned in vendor.lock, needs network)

`git archive` ignores the patched working tree, so the result is exactly the commit pinned by .deps (the release
ships this together with the licences; firstrun.py patches a copy of it on the user's machine).
"""
import os, shutil, subprocess, sys, tarfile, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GR = os.path.join(ROOT, ".deps", "genrecomp")
args = [a for a in sys.argv[1:] if a != "--fetch"]
fetch = "--fetch" in sys.argv[1:]
out = os.path.abspath(args[0] if args else os.path.join(ROOT, "vendor", "genrecomp"))
if fetch:
    import tempfile
    pin = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, "vendor.lock")) if "=" in l and not l.startswith("#"))["genrecomp"]
    GR = os.path.join(tempfile.mkdtemp(prefix="genrecomp-"), "genrecomp")
    subprocess.check_call(["git", "clone", "-q", "https://github.com/sp00nznet/genrecomp", GR])
    subprocess.check_call(["git", "-C", GR, "checkout", "-q", pin])
    subprocess.check_call(["git", "-C", GR, "submodule", "update", "--init", "--recursive", "-q"])


def archive(repo, dest):
    data = subprocess.check_output(["git", "-C", repo, "archive", "--format=tar", "HEAD"])
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        t.extractall(dest, filter="data")


if os.path.isdir(out):
    shutil.rmtree(out)
archive(GR, out)
sub = os.path.join(GR, "ext", "Genesis-Plus-GX")
archive(sub, os.path.join(out, "ext", "Genesis-Plus-GX"))
rev = subprocess.check_output(["git", "-C", GR, "rev-parse", "HEAD"], text=True).strip()
rev2 = subprocess.check_output(["git", "-C", sub, "rev-parse", "HEAD"], text=True).strip()
open(os.path.join(out, "VENDOR_REVISION.txt"), "w").write("genrecomp %s\nGenesis-Plus-GX %s\n" % (rev, rev2))
n = sum(len(f) for _, _, f in os.walk(out))
print("vendor: %s (%d files, genrecomp %s, GPGX %s)" % (out, n, rev[:8], rev2[:8]))
