"""Read / write docs/symbols.json in its canonical format: sorted by address, ONE entry per line (still valid JSON; grep shows whole entries, diffs stay small).
Every tool that writes symbols.json must use save(); loading is plain json (or load() here)."""
import json, os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "symbols.json")


def load(path=PATH):
    return json.load(open(path))


def dumps(doc):
    syms = sorted(doc["symbols"], key=lambda s: int(s["addr"], 16))      # stable: equal addresses keep their order
    head = [(k, v) for k, v in doc.items() if k != "symbols"]
    out = ["{"]
    for k, v in head:
        out.append(" %s: %s," % (json.dumps(k), json.dumps(v, ensure_ascii=False)))
    out.append(' "symbols": [')
    out.append(",\n".join("  " + json.dumps(s, ensure_ascii=False) for s in syms))
    out.append(" ]")
    out.append("}")
    return "\n".join(out) + "\n"


def save(doc, path=PATH):
    s = dumps(doc)
    json.loads(s)           # never write a broken file
    open(path, "w").write(s)


if __name__ == "__main__":      # python3 tools/symfile.py  = rewrite docs/symbols.json in the canonical format
    d = load()
    save(d)
    print("symbols.json: %d entries, canonical format written" % len(d["symbols"]))
