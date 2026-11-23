#!/usr/bin/env python3
"""uikeys.py: which of OUR OWN English UI texts (options menu, help lines, value words, on-screen messages, overlays) are not translated
(2026-11-23, GitHub #18: 'modern' was missing in every language and nobody saw it, because the Mod Workshop only lists keys some language
already has).  Source of truth = the PATCHED C code (.deps/genrecomp after build.sh), not the language files:
  * every function that passes one of its parameters to lk_lang_tr / lk_lang_trw is a 'translating' function (found automatically, also
    wrappers of wrappers); every string literal passed to one of them is a key;
  * plus literals passed to lk_lang_tr / trw directly, and the tables the options code translates by index (lk_id_name, the return values of
    lk_opt_val0 / lk_opt_help, lk_ii_tab, the quick-equip name arrays nm / kind / dnm / dn).
Writes tools/ui_keys.json (sorted list; committed: our own words, no game text) with --write; without it, compares the code with the committed
list and every lang/*.json ui_text (ja: lang/ja_map.json) and prints what is missing per language (exit 1 when a key is missing or the list
is stale).  tools/check_docs.py checks lang/*.json against tools/ui_keys.json (no build needed); tools/modpage.py offers every key of the list.
usage: uikeys.py [--write] [--src .deps/genrecomp] [-v]"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
KEYS = os.path.join(HERE, "ui_keys.json")   # in tools/: every .json in lang/ is built as a language (langbuild)
LIT = r'"((?:[^"\\]|\\.)*)"'
# Keys that are not text a player reads in our font (format-only strings, internal tags) or texts translated elsewhere
RAW_OK = {"MODEL VIEW: %s"}   # debug key (F-key model view), English on purpose
IGNORE = {"", "%s", "%d", "%s: %s", "SABR"}   # SABR = the one-letter labels of the quick-equip overlay (index lt[k]), plain on purpose


def sources(src):
    out = []
    for d in ("src", "ext/Genesis-Plus-GX/core"):
        p = os.path.join(src, d)
        if os.path.isdir(p): out += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".c")]
    texts = [open(f, errors="replace").read() for f in out]
    return [t for t in texts if "lk_lang_tr" in t or "lk_bind_nm" in t]   # only our patched files take part


def args_of(s, i):
    """the argument list text of a call whose '(' is at s[i - 1]"""
    d, j = 1, i
    while d and j < len(s):
        if s[j] == "(": d += 1
        elif s[j] == ")": d -= 1
        elif s[j] == '"':
            j += 1
            while j < len(s) and s[j] != '"': j += 2 if s[j] == "\\" else 1
        j += 1
    return s[i:j - 1]


def body_of(s, i):
    """the text of a { } block starting at s[i] == '{'"""
    d, j = 0, i
    while j < len(s):
        if s[j] == "{": d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0: return s[i:j + 1]
        elif s[j] == '"':
            j += 1
            while j < len(s) and s[j] != '"': j += 2 if s[j] == "\\" else 1
        j += 1
    return s[i:]


def unesc(t): return bytes(t, "utf-8").decode("unicode_escape")


def collect(src):
    texts = sources(src)
    funcs = {}   # name -> (param names, body)
    for s in texts:
        for m in re.finditer(r"^(?:static +)?(?:inline +)?(?:const +)?(?:unsigned +)?\w+[ \*]+([a-z_]\w*)\(([^()\n]*)\)\s*\{", s, re.M):   # function heads start at column 0
            name, params = m.group(1), [p.strip().split()[-1].lstrip("*") for p in m.group(2).split(",") if p.strip() and p.strip() != "void"]
            funcs[name] = (params, body_of(s, m.end() - 1))
    trans = {"lk_lang_tr": [0], "lk_lang_trw": [0]}   # function -> indexes of the parameters that end in a translation
    changed = True
    while changed:
        changed = False
        for name, (params, body) in funcs.items():
            if name in trans: continue
            for t, idxs in list(trans.items()):
                for m in re.finditer(r"\b%s\(" % t, body):
                    a = split_args(args_of(body, m.end()))
                    for k in idxs:
                        if k < len(a) and re.fullmatch(r"\w+", a[k].strip()) and a[k].strip() in params:
                            trans.setdefault(name, []); pi = params.index(a[k].strip())
                            if pi not in trans[name]: trans[name].append(pi); changed = True
    keys, where = set(), {}
    def add(k, w):
        k = unesc(k)
        if k in IGNORE or not re.search(r"[A-Za-z]", k): return
        keys.add(k); where.setdefault(k, w)
    for s in texts:
        for t, idxs in trans.items():
            for m in re.finditer(r"\b%s\(" % t, s):
                a = split_args(args_of(s, m.end()))
                for k in idxs:
                    if k < len(a):
                        for lit in re.findall(LIT, a[k]): add(lit, t)
                        for fn in re.findall(r"\b([a-z_]\w*)\(", a[k]):   # a function result that is translated: its returned literals
                            if fn in funcs and fn not in trans:
                                for lit in re.findall(r"return\s+" + LIT, funcs[fn][1]): add(lit, fn)
        m = re.search(r"static const char \*lk_id_name\[\d+\]\s*=\s*\{", s)
        if m:   # option labels: only options that are on a page (lk_ids_* lists; hidden / removed options are not shown to anyone)
            shown = {int(x) for mm in re.finditer(r"static const int lk_ids_(?!key)\w+\[[\w ]+\]\s*=\s*\{([^}]*)\}", s) for x in re.findall(r"\d+", mm.group(1))}
            for i, lit in enumerate(re.findall(LIT, body_of(s, m.end() - 1))):
                if i in shown: add(lit, "option %d" % i)
        for arr in (r"(?:const )?lk_pg_name\[[\w +]+\]", r"lk_bind_nm\[\w+\]", r"nm\[4\]\[4\]", r"lk_dd_names\[\d+\]", r"lk_scale_names\[\w+\]", r"lk_fx_names\[\w+\]", r"kind\[4\]", r"dnm\[4\]", r"dn\[4\]"):   # the quick-equip tables are [4] / [4][4] (input.c / the tree list have other 'nm' arrays)
            for m in re.finditer(r"static const char \*(?:const )?%s\s*=\s*\{" % arr, s):
                for lit in re.findall(LIT, body_of(s, m.end() - 1)): add(lit, arr)
        m = re.search(r"lk_ii_tab\[\]\s*=\s*\{", s)
        if m:
            for e in re.findall(r"\{\s*-?\w+\s*,\s*" + LIT, body_of(s, m.end() - 1)): add(e, "lk_ii_tab")
    for fn in ("lk_opt_val0", "lk_opt_help"):   # value words / help lines: every literal of the function (also its local word arrays)
        if fn in funcs:
            for lit in re.findall(LIT, funcs[fn][1]): add(lit, fn)
    raw = []   # English written straight into the on-screen message (never translated; user 2026-11-23: 'Fullscreen yes / no is still English')
    for t in texts:
        for m in re.finditer(r"snprintf\(lk_osd_text,[^,]*,\s*" + LIT, t):
            if re.search(r"[A-Za-z]{2}", m.group(1)) and m.group(1) not in RAW_OK: raw.append(m.group(1))
    return keys, where, trans, raw


def split_args(a):
    out, d, cur, i = [], 0, "", 0
    while i < len(a):
        ch = a[i]
        if ch == '"':
            j = i + 1
            while j < len(a) and a[j] != '"': j += 2 if a[j] == "\\" else 1
            cur += a[i:j + 1]; i = j + 1; continue
        if ch in "([{": d += 1
        elif ch in ")]}": d -= 1
        if ch == "," and d == 0: out.append(cur); cur = ""
        else: cur += ch
        i += 1
    out.append(cur)
    return out


def lang_ui():
    out, L = {}, os.path.join(ROOT, "lang")
    for f in sorted(os.listdir(L)):
        if not f.endswith(".json") or f in ("names.json", "friday_hints.json", "en_items.json"): continue
        d = json.load(open(os.path.join(L, f), encoding="utf-8"))
        code = "ja" if f == "ja_map.json" else f[:-5]
        if code == "en_tone": continue   # English (JP) keeps the English menus
        out[code] = d.get("ui_text") or {}
    return out


def main():
    a = sys.argv[1:]
    src = a[a.index("--src") + 1] if "--src" in a else os.path.join(ROOT, ".deps", "genrecomp")
    keys, where, trans, raw = collect(src)
    if "-v" in a: print("translating functions:", ", ".join(sorted(trans)))
    if "--write" in a:
        json.dump(sorted(keys), open(KEYS, "w", encoding="utf-8"), indent=0, ensure_ascii=False); open(KEYS, "a").write("\n")
        print("uikeys: %d keys -> %s" % (len(keys), KEYS)); return 0
    bad = 0
    for r in raw: print("uikeys: on-screen message written in English without translation: %r (use lk_lang_trw)" % r); bad = 1
    old = set(json.load(open(KEYS, encoding="utf-8"))) if os.path.isfile(KEYS) else set()
    if old != keys:
        print("uikeys: tools/ui_keys.json is stale: %d new in the code, %d gone (run with --write)" % (len(keys - old), len(old - keys)))
        for k in sorted(keys - old): print("  new:  %r  (%s)" % (k, where[k]))
        for k in sorted(old - keys): print("  gone: %r" % k)
        bad = 1
    for code, ui in lang_ui().items():
        miss = sorted(keys - set(ui)); extra = sorted(set(ui) - keys)
        print("%-3s %d keys, %d missing%s" % (code, len(ui), len(miss), ", %d not used by the code" % len(extra) if extra else ""))
        for k in miss: print("     missing: %r  (%s)" % (k, where[k]))
        if "-v" in a:
            for k in extra: print("     unused:  %r" % k)
        bad |= bool(miss)
    return bad


if __name__ == "__main__":
    sys.exit(main())
