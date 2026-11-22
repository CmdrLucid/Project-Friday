#!/usr/bin/env python3
"""fridaylang.py: Friday Hints in the languages of the language files (release 2.0, 2026-11-14; user: hints in every language).
lang/friday_hints.json holds per hint "en" / "de" (compiled into the program by tools/patch_friday.py) and, since 2.0, "fr" / "ko" / "ja" ([gentle, clear]).
The other languages go into their language file as extra strings: id FRIDAY_BASE + hint index = the GENTLE level (the only one the runtime shows),
built by tools/langbuild.py (fr, ko) and tools/jplang.py (ja) with the language's own glyph codes; patch_friday.py LK_FRIDAY v4 shows that string when
the loaded language has it, else the English hint.  Layout like patch_friday.words(): her name first, wrapped lines, after every 3 lines a
ContinuePrompt (the box waits for a button), a ContinuePrompt at the end.  Library only (no ROM data written)."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("LANDSTALKER_FRIDAY_JSON") or os.path.join(HERE, "..", "lang", "friday_hints.json")
FRIDAY_BASE = 0xE000
NAME = {"fr": "Friday:", "es": "Friday:", "it": "Friday:", "ru": "Фрайди:", "uk": "Фрайді:", "ko": "프라이데이:", "ja": "フライデー:"}   # es / it (LK_LGES v1): the fan translations keep 'Friday'   # her name in that language's text (fr = the French release keeps 'Friday'; ko / ja = names.json / the Japanese game)


def hints():
    return json.load(open(SRC, encoding="utf-8"))["hints"] if os.path.exists(SRC) else []


def paginate(lines):
    """wrapped lines -> one string with {SoftNewLine}, a {ContinuePrompt} after every 3 lines and at the end"""
    out = ""
    for i, line in enumerate(lines):
        if i:
            if i % 3 == 0: out += "{ContinuePrompt}"
            out += "{SoftNewLine}"
        out += line
    return out + "{ContinuePrompt}"


def latin_text(W, code, text, prefix=None):
    """fr / ko: word wrap with the real glyph widths (tools/langwrap.py) -> string with control codes; prefix = her name for this name variant (LK_FHNAMES v1), default NAME[code]"""
    import langwrap
    s, _ = langwrap.wrap(W, (prefix or NAME[code]) + " " + text)
    return paginate([l for l in s.split("{SoftNewLine}")])


def entries(code):
    """[(string id, gentle text)] of the language code (empty when the json has no texts for it)"""
    return [(FRIDAY_BASE + i, h[code][0]) for i, h in enumerate(hints()) if isinstance(h.get(code), list) and h[code] and h[code][0]]
