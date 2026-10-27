// Remake map editor (remake/tools/editor.py serves this page). Picture coordinates = the original's window (rom_picture.py window.txt):
// a foot (x, y, z) in game units lands on picture pixel (x - y + 1184 - U0 - 1, (x + y) / 2 - z - V0 - 1) (recipes/room_c.py card_at).
"use strict";
const $ = (id) => document.getElementById(id);
let R = null;                 // /api/room: window, cells, cards (as rendered), kinds, overrides
let edits = { move: {}, delete: [], add: [] };
let saved = "";               // JSON of the last saved edits
let undo = [];
let Z = 2, sel = null, placing = null, drag = null, marks = true, cycle = [];
const imgs = {};
const cv = $("cv"), ctx = cv.getContext("2d");

function img(name) {
  if (!name) return null;
  if (!imgs[name]) { const i = new Image(); i.onload = draw; i.src = "/props/" + name; imgs[name] = i; }
  return imgs[name];
}
function scr(f) { const [U0, V0] = R.window; return [f[0] - f[1] + 1184 - U0 - 1, (f[0] + f[1]) / 2 - f[2] - V0 - 1]; }
function add3(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
function sub3(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function r2(v) { return Math.round(v * 4) / 4; }

// the list shown: automatic cards (foot = automatic place + edit) and the added ones
function cards() {
  const out = [];
  for (const c of R.cards) {
    if (c.added) continue;
    const savedMove = (R.overrides.move || {})[c.id] || [0, 0, 0];
    const auto = sub3(c.foot, savedMove);
    const m = edits.move[c.id] || [0, 0, 0];
    out.push({ id: c.id, kind: c.kind, img: c.img, foot: add3(auto, m), rendered: c.deleted ? null : c.foot, deleted: edits.delete.includes(c.id) });
  }
  const rend = {};
  for (const c of R.cards) if (c.added) rend[c.id] = c.foot;
  edits.add.forEach((a, i) => {
    const id = "add:" + i, kind = a.kind;
    out.push({ id, kind, img: kind + ".png", foot: [a.x, a.y, a.z], rendered: rend[id] || null, deleted: false, added: true });
  });
  return out;
}
function rect(c) {
  const [u, v] = scr(c.foot); const i = img(c.img);
  const w = i && i.naturalWidth ? i.naturalWidth : 30, h = i && i.naturalHeight ? i.naturalHeight : 40;
  return [u - Math.floor(w / 2), v - h + 1, w, h];
}
function changed(c) { return !c.rendered || Math.abs(c.foot[0] - c.rendered[0]) + Math.abs(c.foot[1] - c.rendered[1]) + Math.abs(c.foot[2] - c.rendered[2]) > 0.01; }

function draw() {
  if (!R) return;
  cv.width = 1056 * Z; cv.height = 912 * Z; ctx.setTransform(Z, 0, 0, Z, 0, 0); ctx.imageSmoothingEnabled = false;
  for (const c of cards()) {
    const [x, y, w, h] = rect(c); const [u, v] = scr(c.foot); const isSel = sel === c.id;
    if (c.deleted) {
      ctx.strokeStyle = "#ff5050"; ctx.lineWidth = 2 / Z; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y + h); ctx.moveTo(x + w, y); ctx.lineTo(x, y + h); ctx.stroke();
      continue;
    }
    if (changed(c) || isSel) {                                    // not in the render yet (or selected): show the sprite itself at its new place
      const i = img(c.img); if (i && i.complete) { ctx.globalAlpha = isSel ? 0.85 : 0.75; ctx.drawImage(i, x, y); ctx.globalAlpha = 1; }
      if (changed(c) && c.rendered) {                             // where it is in the render now
        const [ou, ov] = scr(c.rendered); ctx.strokeStyle = "rgba(80,255,120,.7)"; ctx.setLineDash([2 / Z, 2 / Z]); ctx.lineWidth = 1 / Z;
        ctx.beginPath(); ctx.moveTo(ou, ov); ctx.lineTo(u, v); ctx.stroke(); ctx.setLineDash([]);
      }
    }
    if (isSel) { ctx.strokeStyle = "#50e0ff"; ctx.lineWidth = 2 / Z; ctx.strokeRect(x - .5, y - .5, w + 1, h + 1); }
    else if (changed(c)) { ctx.strokeStyle = "#50ff78"; ctx.lineWidth = 1 / Z; ctx.strokeRect(x, y, w, h); }
    if (marks || isSel) { ctx.fillStyle = isSel ? "#50e0ff" : changed(c) ? "#50ff78" : "#f0c060"; ctx.beginPath(); ctx.arc(u + .5, v + .5, 2.2, 0, 7); ctx.fill(); }
  }
  info();
}
function info() {
  const c = cards().find((c) => c.id === sel);
  if (!c) { $("info").textContent = placing ? "Neu setzen: " + placing + "\nIn die Karte klicken (Esc = abbrechen)." : "Nichts ausgewählt. Auf ein Sprite klicken."; return; }
  const m = edits.move[c.id];
  $("info").textContent = "Sprite: " + c.kind + "\nName: " + c.id + "\nFuß (x, y, Höhe): " + c.foot.map((v) => v.toFixed(1)).join(", ") +
    "\nFeld: " + Math.floor((c.foot[0] - R.O) / 16) + ", " + Math.floor((c.foot[1] - R.O) / 16) +
    (m ? "\nVerschoben um: " + m.map((v) => v.toFixed(1)).join(", ") : "") + (c.deleted ? "\nGELÖSCHT" : "") + (changed(c) ? "\n(noch nicht gerendert)" : "");
}
function status(t) { $("status").textContent = t; }
function dirty() { status(JSON.stringify(edits) === saved ? "gespeichert" : "nicht gespeichert"); }
function push() { undo.push(JSON.stringify(edits)); if (undo.length > 200) undo.shift(); }

function setFoot(c, f) {
  if (c.added) { const a = edits.add[+c.id.slice(4)]; a.x = r2(f[0]); a.y = r2(f[1]); a.z = r2(f[2]); }
  else {
    const auto = sub3(c.foot, edits.move[c.id] || [0, 0, 0]);
    edits.move[c.id] = sub3(f, auto).map(r2);
    if (edits.move[c.id].every((v) => Math.abs(v) < 1e-3)) delete edits.move[c.id];
  }
}
function nudge(du, dv, dz) {                                       // screen pixels (on the ground) and height
  const c = cards().find((c) => c.id === sel); if (!c || c.deleted) return;
  push(); setFoot(c, [c.foot[0] + dv + du / 2, c.foot[1] + dv - du / 2, c.foot[2] + dz]); dirty(); draw();
}
function pt(e) { const b = cv.getBoundingClientRect(); return [(e.clientX - b.left) / Z, (e.clientY - b.top) / Z]; }
function hits(p) {
  return cards().filter((c) => { const [x, y, w, h] = rect(c); return p[0] >= x && p[0] < x + w && p[1] >= y && p[1] < y + h; })
    .sort((a, b) => (b.foot[0] + b.foot[1] + b.foot[2]) - (a.foot[0] + a.foot[1] + a.foot[2]));   // nearest to the camera first
}
function ground(p) {                                               // picture point -> the highest cell surface along the view ray
  const [U0, V0] = R.window; const U = p[0] + U0 + 1, V = p[1] + V0 + 1;
  const top = {}; for (const [x, y, h] of R.cells) top[x + "," + y] = h;
  const hs = [...new Set(R.cells.map((c) => c[2]))].sort((a, b) => b - a);
  for (const z of hs) {
    const x = (U - 1184) / 2 + V + z, y = x - (U - 1184);
    if (top[Math.floor((x - R.O) / 16) + "," + Math.floor((y - R.O) / 16)] === z) return [r2(x), r2(y), z];
  }
  const x = (U - 1184) / 2 + V; return [r2(x), r2(x - (U - 1184)), 0];
}

cv.addEventListener("mousedown", (e) => {
  if (!R) return; const p = pt(e);
  if (placing) { push(); const f = ground(p); edits.add.push({ kind: placing, x: f[0], y: f[1], z: f[2] }); sel = "add:" + (edits.add.length - 1); placing = null; dirty(); draw(); return; }
  const h = hits(p).filter((c) => !c.deleted || c.id === sel);
  if (!h.length) { sel = null; draw(); return; }
  const key = h.map((c) => c.id).join("|");
  let c = h[0];
  if (cycle.key === key && h.some((x) => x.id === sel) && !e.shiftKey) {   // clicked the same stack again: the next sprite behind
    if (cycle.moved) c = h.find((x) => x.id === sel); else c = h[(h.findIndex((x) => x.id === sel) + 1) % h.length];
  }
  cycle = { key, moved: false };
  sel = c.id; drag = { p, foot: c.foot.slice(), pushed: false }; draw();
});
window.addEventListener("mousemove", (e) => {
  if (!drag) return; const p = pt(e); const du = p[0] - drag.p[0], dv = p[1] - drag.p[1];
  if (!drag.pushed && Math.abs(du) + Math.abs(dv) < 1.5) return;
  const c = cards().find((c) => c.id === sel); if (!c || c.deleted) return;
  if (!drag.pushed) { push(); drag.pushed = true; cycle.moved = true; }
  setFoot(c, [drag.foot[0] + dv + du / 2, drag.foot[1] + dv - du / 2, drag.foot[2]]); dirty(); draw();
});
window.addEventListener("mouseup", () => { drag = null; });
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT") return;
  const s = e.shiftKey ? 4 : 1;
  if (e.ctrlKey && e.key.toLowerCase() === "z") { e.preventDefault(); doUndo(); return; }
  if (e.ctrlKey && e.key.toLowerCase() === "s") { e.preventDefault(); save(); return; }
  const k = { ArrowLeft: [-s, 0, 0], ArrowRight: [s, 0, 0], ArrowUp: [0, -s, 0], ArrowDown: [0, s, 0], PageUp: [0, 0, s], PageDown: [0, 0, -s] }[e.key];
  if (k && sel) { e.preventDefault(); nudge(...k); return; }
  if ((e.key === "Delete" || e.key === "Backspace") && sel) { e.preventDefault(); del(); return; }
  if (e.key === "Escape") { placing = null; sel = null; draw(); }
  if (e.key === "m" || e.key === "M") toggleMarks();
});
function del() {
  const c = cards().find((c) => c.id === sel); if (!c) return; push();
  if (c.added) { edits.add.splice(+c.id.slice(4), 1); sel = null; }
  else if (c.deleted) edits.delete = edits.delete.filter((x) => x !== c.id);
  else edits.delete.push(c.id);
  dirty(); draw();
}
function doUndo() { if (!undo.length) return; edits = JSON.parse(undo.pop()); dirty(); draw(); }
function toggleMarks() { marks = !marks; $("marks").classList.toggle("on", marks); draw(); }
async function save() {
  const r = await fetch("/api/save", { method: "POST", body: JSON.stringify(edits) });
  if (r.ok) { saved = JSON.stringify(edits); dirty(); } else status("Speichern fehlgeschlagen");
}
async function render() {
  await save(); await fetch("/api/render", { method: "POST" }); $("render").disabled = true;
  const t0 = Date.now();
  const poll = async () => {
    const s = await (await fetch("/api/render")).json();
    if (s.state === "running") { status("rendert ... " + Math.round((Date.now() - t0) / 1000) + " s (dauert etwa 1 Minute)"); setTimeout(poll, 2000); return; }
    $("render").disabled = false;
    if (s.state === "failed") { status("Rendern fehlgeschlagen (Meldung im Konsole-Fenster)"); console.log(s.log); return; }
    await load(); status("gerendert in " + Math.round(s.took) + " s");
  };
  poll();
}
function zoom(z) { Z = Math.max(1, Math.min(6, z)); $("zv").textContent = Z + "x"; for (const i of [$("bgo"), $("bgr")]) { i.style.width = 1056 * Z + "px"; i.style.height = 912 * Z + "px"; } $("stage").style.width = 1056 * Z + "px"; $("stage").style.height = 912 * Z + "px"; draw(); }
async function load() {
  const r = await fetch("/api/room");
  if (!r.ok) { status("Noch kein Render da: bitte 'Rendern' drücken"); R = null; return; }
  R = await r.json(); const ov = R.overrides || {};
  edits = { move: Object.assign({}, ov.move || {}), delete: (ov.delete || []).slice(), add: (ov.add || []).map((a) => Object.assign({}, a)) };
  saved = JSON.stringify(edits); undo = [];
  $("room").textContent = "Raum " + R.room + " · " + R.cards.length + " Sprites";
  const t = "?t=" + Date.now(); $("bgo").src = "/img/original.png"; $("bgr").src = "/img/render.png" + t;
  const k = $("kinds"); k.innerHTML = "";
  for (const name of R.kinds) {
    const b = document.createElement("button"); b.innerHTML = '<img src="/props/' + name + '.png" alt=""><span>' + name + "</span>";
    b.onclick = () => { placing = name; sel = null; draw(); }; k.appendChild(b);
  }
  dirty(); draw();
}
$("fade").oninput = () => { $("bgr").style.opacity = $("fade").value / 100; };
$("zin").onclick = () => zoom(Z + 1); $("zout").onclick = () => zoom(Z - 1);
$("view").addEventListener("wheel", (e) => { if (e.ctrlKey) { e.preventDefault(); zoom(Z + (e.deltaY < 0 ? 1 : -1)); } }, { passive: false });
$("marks").onclick = toggleMarks; $("undo").onclick = doUndo; $("save").onclick = save; $("render").onclick = render;
$("del").onclick = del; $("up").onclick = () => nudge(0, 0, 1); $("down").onclick = () => nudge(0, 0, -1);
$("reset").onclick = () => { const c = cards().find((c) => c.id === sel); if (!c || c.added) return; push(); delete edits.move[c.id]; edits.delete = edits.delete.filter((x) => x !== c.id); dirty(); draw(); };
window.addEventListener("beforeunload", (e) => { if (JSON.stringify(edits) !== saved) { e.preventDefault(); e.returnValue = ""; } });
$("bgr").style.opacity = 1;
zoom(2); load().then(() => { const v = $("view"); v.scrollTo((560 * Z - v.clientWidth / 2), (450 * Z - v.clientHeight / 2)); });   // start on the village
