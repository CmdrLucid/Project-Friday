#!/bin/bash
# usage: run.sh GENRECOMP_DIR BUILD_DIR OUT_DIR [count] [trials] [seed]   -- differential instruction fuzz (needs libsdl2-dev, capstone)
set -e
G=$1; B=$2; D=$3; N=${4:-4000}; T=${5:-6}; S=${6:-1}
cd "$(dirname "$0")"
python3 mk.py $N $S
rm -rf out && python3 $G/tools/recompiler/generate.py fuzz.bin -o out -c fuzz.json > $D/fuzz_gen.log 2>&1 || { tail -5 $D/fuzz_gen.log; exit 1; }
echo "unsupported / TODO lines in generated code: $(grep -c 'TODO\|UNHANDLED' out/*.c | awk -F: '{s+=$2} END {print s}')"
INC=$(find $G/ext/Genesis-Plus-GX/core -type d | sed 's/^/-I/')
gcc -O1 -w -DLSB_FIRST -DUSE_32BPP_RENDERING -I$G/include -I$G/src -Iout $INC h.c out/*.c -o $D/insnfuzz $B/libgenrecomp.a $B/libgenplusgx_hw.a $(sdl2-config --libs) -lm
$D/insnfuzz --headless fuzz.bin tests.txt $T $S > $D/fuzz_result.txt 2>$D/fuzz_err.txt || true
tail -1 $D/fuzz_result.txt
# show the mismatching instructions (first mismatch per instruction), joined with the instruction text
python3 - "$D/fuzz_result.txt" <<'PY'
import sys, collections
tests = {}
for l in open('tests.txt'):
    n, rest = l.split(' ', 1); tests[int(n)] = rest.split('|', 1)[1].strip()
seen = collections.OrderedDict(); by = collections.Counter()
for l in open(sys.argv[1]):
    if l.startswith('MISMATCH'):
        idx = int(l.split()[1]); m = tests[idx].split()[0]
        by[m] += 1
        seen.setdefault(idx, l.strip())
print('mismatching instruction forms per mnemonic:', dict(by.most_common(40)))
for idx, l in list(seen.items())[:25]:
    print('%-34s %s' % (tests[idx], l.split('|', 1)[1].strip()[:150]))
PY
