#!/usr/bin/env python3
"""friday_overview.py [out.html]: readable overview of the Friday hints (lang/friday_hints.json) for checking them while playing:
when each hint comes (story stage, place, item, event in plain German) and what Friday / Flora says.  Our own text only (no ROM data).
Default output: ~/Project-Friday-Test/Friday_Hinweise.html (open it in the browser)."""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "..", "lang", "friday_hints.json")))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Project-Friday-Test/Friday_Hinweise.html")

STAGE = {   # main story stage (game's GetFlagProgress) -> what has happened, German
    0: "Spielbeginn", 1: "ein Dorfbewohner in Massan hat von der kaputten Brücke erzählt", 2: "Fara wurde entführt",
    3: "du hast das Ritual in Gumi belauscht", 4: "Fara ist gerettet", 5: "du hast den roten Juwel vom Bürgermeister (Massan)",
    6: "du hast den versteckten Dorfbewohner in Ryuma gesprochen", 7: "Ryuma erlaubt dir, ins Räuberversteck zu gehen",
    8: "die Räuberbande ist besiegt", 9: "du hast den Passierschein (Safety Pass)", 10: "Mercator, erster Schritt Richtung Schloss (unsicher)",
    12: "du hast Arthur an der Schloss-Hintertür gesehen", 13: "das Mädchen bei Madame Yard hat die Wahrsagerin erwähnt",
    14: "die Wahrsagerin hat ihren Zauber gewirkt", 15: "Arthur hat dir Zugang zum Schloss verschafft",
    16: "der Herzog hat den Raum nach dem ersten Treffen verlassen", 17: "ein Diener hat dich ins Schlafzimmer gebracht",
    18: "die Küchenfrau hat zum Bankett gerufen", 19: "du warst beim Bankett", 20: "du hast nach dem Bankett geschlafen",
    21: "Krypta: Rätselteil geschafft (unsicher)", 22: "Armreif (Armlet) geholt (unsicher)", 23: "du hast Mir in seinem Turm getroffen",
    24: "Zak ist aus dem Verlies von Mercator davongeflogen", 25: "Cutter hat dir Einsteins Pfeife gegeben", 26: "der Leuchtturm leuchtet wieder",
    27: "Marley ist besiegt (Verla-Minen)", 28: "du hast den Herzog in den Seeschrein gehen sehen", 29: "Seeschrein geschafft, Mir hat dich gerettet",
    30: "du hast Golas Auge benutzt", 31: "der Teleporter in Mercator zu King Nole's Cave ist offen",
}
ROOM = {   # room ranges used by the hints -> place, German
    "0-30": "im Sumpfschrein", "111-114": "in den Arenen am Ende", "115-138": "in King Nole's Palast", "144-172": "in King Nole's Cave",
    "174-182": "im Wasserfallschrein", "184-226": "im Räuberversteck", "227-269": "in den Verla-Minen", "270-290": "im Brunnen von Destel",
    "291-354": "im Seeschrein", "355-423": "im Labyrinth", "51-62": "im Schloss von Mercator", "601-607": "in Gumi", "610-629": "in Ryuma",
    "630-710": "in Mercator", "646-659": "in der Krypta (Mercator)", "711-721": "in Verla", "726-736": "in Destel", "737-749": "in Kazalt",
    "750-784": "in Mirs Turm",
}
ITEM = {"1E": "den Sonnenstein", "1F": "den Armreif (Armlet)", "20": "Einsteins Pfeife", "31": "den Götzenstein (Idol Stone)"}
FLAG = {"00.6": "die Tür des Sumpfschreins ist offen", "13.0": "du sitzt im Verlies von Mercator", "17.6": "du hast den lila Juwel in Mirs Turm genommen",
        "20.4": "du hast die Prinzessin im Verlies gefunden", "20.6": "Arthur hat dir von der Flucht des Herzogs erzählt",
        "26.7": "Dex ist besiegt", "28.7": "du hast den Herzog auf dem Floß bei Destel gesehen",
        "2B.1": "das zweite Floß im Labyrinth liegt bereit", "2B.7": "der Herzog hat dich im Labyrinth verspottet"}
DE_STR = json.load(open(os.path.join(HERE, "..", "lang", "de.json")))["strings"]
def heard_txt(ids):
    """heard:A|B ids -> short German quote of the line(s) (de.json 't', {codes} stripped, first 40 chars)"""
    out = []
    for i in ids.split("|"):
        t = re.sub(r"\{[^}]*\}", " ", DE_STR.get(i.upper(), {}).get("t", "")); t = " ".join(t.split())
        out.append(("'" + t[:40] + ("..." if len(t) > 40 else "") + "'") if t else i)
    return " / ".join(out)
UNSURE = set()
md = open(os.path.join(HERE, "..", "docs", "FRIDAY_HINTS.md")).read()
sec = md.split("## 6. UNSURE list", 1)[-1]
for m in re.finditer(r"`(stage[0-9a-z_*]+)`", sec): UNSURE.add(m.group(1))

def when(h):
    st = 0; extra = []
    for c in h["when"]:
        c = c.replace(" ", "")
        if c.startswith("stage>="): st = int(c[7:])
        elif c.startswith("room:"): extra.append(ROOM.get(c[5:], "Raum " + c[5:]))
        elif c.startswith("!item:"): extra.append("du hast " + ITEM.get(c[6:], "Gegenstand " + c[6:]) + " noch nicht")
        elif c.startswith("item:"): extra.append("du hast " + ITEM.get(c[5:], "Gegenstand " + c[5:]))
        elif c.startswith("flag:"): extra.append(FLAG.get(c[5:], "Ereignis " + c[5:]))
        elif c.startswith("!flag:"): extra.append("nicht: " + FLAG.get(c[6:], "Ereignis " + c[6:]))
        elif c.startswith("!heard:"): extra.append("nicht gehört: " + heard_txt(c[7:]))
        elif c.startswith("heard:"): extra.append("nachdem man gehört hat: " + heard_txt(c[6:]))
    return st, extra

rows = []
for n, h in enumerate(D["hints"], 1):
    st, extra = when(h)
    uns = any(u == h["id"] or (u.endswith("*") and h["id"].startswith(u[:-1])) for u in UNSURE)
    rows.append((n, h["id"], st, extra, h["de"][0].replace("|", " "), h["en"][0].replace("|", " "), uns))

E = html.escape
out = ["<!doctype html><html lang='de'><meta charset='utf-8'><title>Friday-Hinweise</title><style>",
       "body{font-family:sans-serif;background:#1b1a2e;color:#eee;margin:24px;max-width:1100px}h1{font-size:22px}",
       "table{border-collapse:collapse;width:100%}td,th{padding:6px 8px;border-bottom:1px solid #3a3860;vertical-align:top;font-size:14px}",
       "th{text-align:left;color:#b9a7ff}.st{color:#9fd;width:26%}.de{font-size:15px}.en{color:#999;font-size:12px}",
       ".id{color:#777;font-size:11px}.u{background:#4a2c2c}.tag{background:#a33;color:#fff;border-radius:3px;padding:0 4px;font-size:11px}",
       "tr.sth td{background:#2a2850;color:#cfc3ff;font-weight:bold}",
       "textarea{width:100%;min-height:44px;box-sizing:border-box;background:#11101f;color:#fff;border:1px solid #4a4880;border-radius:4px;font-size:14px;padding:4px}",
       "textarea.has{border-color:#e8c068}td.k{width:34%}.bar{position:sticky;top:0;background:#1b1a2e;padding:8px 0;border-bottom:2px solid #e8c068;z-index:2;display:flex;gap:10px;align-items:center;flex-wrap:wrap}",
       "button{background:#e8c068;color:#1b1a2e;border:0;border-radius:4px;padding:8px 14px;font-size:15px;font-weight:bold;cursor:pointer}#info{color:#9fd;font-size:13px}</style>",
       "<h1>Friday-Hinweise (Select-Taste): wann kommt welcher Hinweis</h1>",
       "<p>Friday sagt immer den Hinweis der <b>letzten</b> Zeile, deren Bedingung erfüllt ist. Die Story-Stufe stammt aus der eigenen "
       "Fortschrittstabelle des Spiels (dieselbe, nach der die Dorfbewohner reden). Zeilen mit Ort gelten nur, solange du dort bist. "
       "<span class='tag'>unsicher</span> = vom Agenten geraten, bitte besonders prüfen.</p>",
       "<p><b>Kommentare:</b> rechts in das Feld schreiben (neuer Text, falsche Bedingung, ...). Der Browser merkt sich alles beim Tippen. "
       "Am Ende <b>Kommentare speichern</b> drücken: die Datei <code>Friday_Kommentare.txt</code> landet in <code>~/Downloads</code>, Claude liest sie von dort. "
       "<b>Datei laden</b> holt eine gespeicherte Datei wieder in die Felder.</p>",
       "<div class='bar'><button id='save'>Kommentare speichern</button><button id='loadb'>Datei laden</button><input type='file' id='load' accept='.txt' hidden><span id='info'></span></div>",
       "<table><tr><th>Nr</th><th>Wann</th><th>Was Flora sagt</th><th>Dein Kommentar</th></tr>"]
cur = None
for n, i, st, extra, de, en, uns in rows:
    if st != cur:
        cur = st; out.append("<tr class='sth'><td colspan='4'>Stufe %d: %s</td></tr>" % (st, E(STAGE.get(st, "?"))))
    w = "ab hier" if not extra else "und " + " und ".join(E(x) for x in extra)
    out.append("<tr%s><td>%d</td><td class='st'>%s%s<div class='id'>%s</div></td><td><div class='de'>%s</div><div class='en'>%s</div></td><td class='k'><textarea data-n='%d' data-id='%s'></textarea></td></tr>" % (
        " class='u'" if uns else "", n, w, " <span class='tag'>unsicher</span>" if uns else "", E(i), E(de), E(en), n, E(i)))
out.append("</table>")
# comments: kept in the browser while typing (localStorage, may be unavailable: then only the file counts), saved as a text file to ~/Downloads (2026-10-31, user: 'Kommentare direkt in die HTML schreiben und speichern')
out.append(r"""<script>
const K = 'friday_kommentare_v1', T = [...document.querySelectorAll('textarea')], info = document.getElementById('info');
function mark() { let n = 0; T.forEach(t => { t.classList.toggle('has', t.value.trim() !== ''); if (t.value.trim()) n++; }); info.textContent = n + ' Kommentar(e)'; }
function keep() { const o = {}; T.forEach(t => { if (t.value.trim()) o[t.dataset.id] = t.value; }); try { localStorage.setItem(K, JSON.stringify(o)); } catch (e) {} mark(); }
try { const o = JSON.parse(localStorage.getItem(K) || '{}'); T.forEach(t => { if (o[t.dataset.id]) t.value = o[t.dataset.id]; }); } catch (e) {}
T.forEach(t => t.addEventListener('input', keep)); mark();
document.getElementById('save').onclick = () => {
  let s = 'Friday-Hinweise: Kommentare (' + new Date().toLocaleString('de-DE') + ')\n\n';
  T.forEach(t => { if (t.value.trim()) s += '#' + t.dataset.n + ' [' + t.dataset.id + ']\n' + t.value.trim() + '\n\n'; });
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([s], { type: 'text/plain;charset=utf-8' })); a.download = 'Friday_Kommentare.txt';
  document.body.appendChild(a); a.click(); a.remove(); info.textContent = 'gespeichert: Friday_Kommentare.txt (Downloads)';
};
document.getElementById('loadb').onclick = () => document.getElementById('load').click();
document.getElementById('load').onchange = e => { const f = e.target.files[0]; if (!f) return; f.text().then(s => {
  const parts = s.split(/^#\d+ \[([^\]]+)\]\n/m); const o = {}; for (let i = 1; i + 1 < parts.length; i += 2) o[parts[i]] = parts[i + 1].trim();
  T.forEach(t => { if (o[t.dataset.id] !== undefined) t.value = o[t.dataset.id]; }); keep(); info.textContent = 'geladen: ' + Object.keys(o).length + ' Kommentar(e)'; }); };
</script></html>""")
open(OUT, "w", encoding="utf-8").write("\n".join(out))
print("written", OUT, len(rows), "hints,", sum(r[6] for r in rows), "unsure")
