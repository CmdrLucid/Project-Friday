// Remake map editor (remake/tools/editor.py serves this page). Every view (game view, turned 90 / 180 / 270) comes with a render WITHOUT the
// editable cards and its projection (recipes/room_c.py editor_view): editor pixel = A * (x, y, z, 1) for game units; row 3 = depth (smaller = nearer).
// The page draws the cards itself where they are now, so a moved card shows only at its new place.
"use strict";
const $ = (id) => document.getElementById(id);
let R = null;                 // /api/room: window, cells, views, cards (as rendered), kinds, overrides
let V = null;                 // current view
let edits = { move: {}, delete: [], add: [] };
let saved = "";               // JSON of the last saved edits
let undo = [];
let Z = 2, sel = null, placing = null, drag = null, marks = false, finished = false, cycle = {};
let stamp = "";
const imgs = {};
const masks = {};
const hds = {};               // view name -> {w, h, hd: Float32Array} ground position along the view of fences / terrain / cliffs (NaN = none)             // view name -> [canvas per house: opaque where that house is seen] (from the view's mask PNG)
const cv = $("cv"), ctx = cv.getContext("2d");

function img(name) {
  if (!name) return null;
  if (!imgs[name]) { const i = new Image(); i.onload = draw; i.src = "/props/" + name; imgs[name] = i; }
  return imgs[name];
}
function add3(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
function sub3(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function r2(v) { return Math.round(v * 4) / 4; }
function proj(g) { const A = V.A; return [0, 1, 2].map((i) => A[i][0] * g[0] + A[i][1] * g[1] + A[i][2] * g[2] + A[i][3]); }
function off(c) { return (V.offs && V.offs[c.id]) || (V.name === "game" ? [0, 0, 0] : [-7.5, -7.5, 0]); }
function solve2(du, dv) {                                          // screen delta -> ground delta (x, y) at the same height
  const A = V.A, a = A[0][0], b = A[0][1], c = A[1][0], d = A[1][1], det = a * d - b * c;
  return [(d * du - b * dv) / det, (-c * du + a * dv) / det];
}

// the list shown: automatic cards (foot = automatic place + edit) and the added ones, far first
function cards() {
  const out = [];
  for (const c of R.cards) {
    if (c.added) continue;
    const savedMove = ((R.rendered_with || R.overrides).move || {})[c.id] || [0, 0, 0];   // the edits the render was made with
    const auto = sub3(c.foot, savedMove);
    const m = edits.move[c.id] || [0, 0, 0];
    out.push({ id: c.id, kind: c.kind, img: c.img, foot: add3(auto, m), rendered: c.deleted ? null : c.foot, deleted: edits.delete.includes(c.id) });
  }
  const rend = {};
  for (const c of R.cards) if (c.added) rend[c.id] = c.foot;
  edits.add.forEach((a, i) => {
    const id = "add:" + i;
    out.push({ id, kind: a.kind, img: a.kind + ".png", foot: [a.x, a.y, a.z], rendered: rend[id] || null, deleted: false, added: true });
  });
  for (const c of out) { const p = proj(add3(c.foot, off(c))); c.u = p[0]; c.v = p[1]; c.depth = p[2]; }
  return out.sort((a, b) => b.depth - a.depth);
}
function rect(c) {
  const i = img(c.img);
  const w = (i && i.naturalWidth ? i.naturalWidth : 30) * V.s, h = (i && i.naturalHeight ? i.naturalHeight : 40) * V.s;
  if (V.name === "game") return [Math.floor(c.u - 0.5 - w / 2), Math.round(c.v - h), w, h];   // whole pixels as in the original (measured against game.png)
  return [c.u - w / 2, c.v - h, w, h];
}
// sort_cards' footprint rule: -1 = the foot stands BEHIND the house (the house covers the card), +1 in front, 0 unclear
function side(F, b) {
  const m = 1, vx = V.A[2][0], vy = V.A[2][1];                    // depth gradient = horizontal view direction into the scene
  if (F[0] > b[0] + m && F[0] < b[1] - m && F[1] > b[2] + m && F[1] < b[3] - m) return -1;   // foot under the roof (overhang): the house covers it, as in the render
  const fx = vx > 1e-6 ? F[0] <= b[0] + m : vx < -1e-6 ? F[0] >= b[1] - m : false, fy = vy > 1e-6 ? F[1] <= b[2] + m : vy < -1e-6 ? F[1] >= b[3] - m : false;
  const bx = vx > 1e-6 ? F[0] >= b[1] - m : vx < -1e-6 ? F[0] <= b[0] + m : false, by = vy > 1e-6 ? F[1] >= b[3] - m : vy < -1e-6 ? F[1] <= b[2] + m : false;
  if ((fx || fy) && !(bx || by)) return 1;
  if ((bx || by) && !(fx || fy)) return -1;
  return 0;
}
function loadMask(v) {
  if (masks[v.name] || !v.mask || !R.houses) return;
  masks[v.name] = "loading";
  const i = new Image();
  i.onload = () => {
    const w = i.naturalWidth, h = i.naturalHeight, c0 = document.createElement("canvas"); c0.width = w; c0.height = h;
    const g = c0.getContext("2d"); g.drawImage(i, 0, 0); const src = g.getImageData(0, 0, w, h).data;
    masks[v.name] = R.houses.map((_, k) => {
      const c = document.createElement("canvas"); c.width = w; c.height = h; const gc = c.getContext("2d"); const d = gc.createImageData(w, h);
      for (let p = 0; p < w * h; p++) if (src[p * 4 + 3] > 128 && Math.round(src[p * 4] / R.house_step) === k + 1) d.data[p * 4 + 3] = 255;
      gc.putImageData(d, 0, 0); return c;
    });
    draw();
  };
  i.onerror = () => { masks[v.name] = null; };
  i.src = "/img/" + v.mask + "?t=" + stamp;
}
function loadHd(v) {
  if (hds[v.name] || !v.hd) return;
  hds[v.name] = "loading";
  const i = new Image();
  i.onload = () => {
    const w = i.naturalWidth, h = i.naturalHeight, c0 = document.createElement("canvas"); c0.width = w; c0.height = h;
    const g = c0.getContext("2d"); g.drawImage(i, 0, 0); const d = g.getImageData(0, 0, w, h).data; const hd = new Float32Array(w * h);
    for (let p = 0; p < w * h; p++) {
      if (d[p * 4 + 3] < 128) { hd[p] = NaN; continue; }
      const t = d[p * 4] / 255, f = d[p * 4 + 1] / 255; let tf = (Math.round(t * 16 - f) + f) / 16;   // R = t, G = t * 16 mod 1 (room_c.py render_hd)
      if (Math.abs(tf - t) > 1.5 / 255) tf = t;
      hd[p] = v.hd_lo + tf * (v.hd_hi - v.hd_lo);
    }
    hds[v.name] = { w, h, hd }; draw();
  };
  i.onerror = () => { hds[v.name] = null; };
  i.src = "/img/" + v.hd + "?t=" + stamp;
}
const tmp = document.createElement("canvas"), tg = tmp.getContext("2d", { willReadFrequently: true });
function drawCard(c, i, x, y, w, h) {                              // the card, minus the pixels of every house standing in front of its foot
  const ms = masks[V.name]; const o = add3(c.foot, off(c));
  const front = Array.isArray(ms) ? R.houses.map((b, k) => side(o, b) < 0 ? ms[k] : null).filter(Boolean) : [];
  const H_ = hds[V.name] && hds[V.name].hd ? hds[V.name] : null;
  if (!front.length && !H_) { ctx.drawImage(i, x, y, w, h); return; }
  const W = Math.ceil(w) + 1, H = Math.ceil(h) + 1; tmp.width = W; tmp.height = H; tg.imageSmoothingEnabled = false;
  tg.drawImage(i, x - Math.floor(x), y - Math.floor(y), w, h);
  tg.globalCompositeOperation = "destination-out";
  for (const m of front) tg.drawImage(m, -Math.floor(x), -Math.floor(y), V.w, V.h);
  tg.globalCompositeOperation = "source-over";
  if (H_) {                                                        // fences / terrain in FRONT of the foot (by more than 2 units) cover the card (sort_cards' fields)
    const fh = o[0] * V.hv[0] + o[1] * V.hv[1] - 2, x0 = Math.floor(x), y0 = Math.floor(y);
    const im = tg.getImageData(0, 0, W, H), dd = im.data; let hit = false;
    for (let j = 0; j < H; j++) {
      const yy = y0 + j; if (yy < 0 || yy >= H_.h) continue;
      for (let k = 0; k < W; k++) {
        const xx = x0 + k; if (xx < 0 || xx >= H_.w || !dd[(j * W + k) * 4 + 3]) continue;
        if (H_.hd[yy * H_.w + xx] < fh) { dd[(j * W + k) * 4 + 3] = 0; hit = true; }
      }
    }
    if (hit) tg.putImageData(im, 0, 0);
  }
  ctx.drawImage(tmp, Math.floor(x), Math.floor(y));
}
function changed(c) { return !c.rendered || Math.abs(c.foot[0] - c.rendered[0]) + Math.abs(c.foot[1] - c.rendered[1]) + Math.abs(c.foot[2] - c.rendered[2]) > 0.01; }

function draw() {
  if (!R || !V) return;
  cv.width = Math.round(V.w * Z); cv.height = Math.round(V.h * Z); ctx.setTransform(Z, 0, 0, Z, 0, 0); ctx.imageSmoothingEnabled = false;
  for (const c of cards()) {
    const [x, y, w, h] = rect(c); const isSel = sel === c.id; const i = img(c.img);
    if (!finished || isSel || changed(c) || c.deleted) {          // 'Fertiges Bild' shows the render's own sprites; only changes are drawn on top
      if (i && i.complete && i.naturalWidth) { ctx.globalAlpha = c.deleted ? 0.3 : 1; if (isSel || c.deleted) ctx.drawImage(i, x, y, w, h); else drawCard(c, i, x, y, w, h); ctx.globalAlpha = 1; }
    }
    if (c.deleted) {
      ctx.strokeStyle = "#ff5050"; ctx.lineWidth = 2 / Z; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y + h); ctx.moveTo(x + w, y); ctx.lineTo(x, y + h); ctx.stroke();
      continue;
    }
    if (isSel) { ctx.strokeStyle = "#50e0ff"; ctx.lineWidth = 2 / Z; ctx.strokeRect(x - .5, y - .5, w + 1, h + 1); }
    else if (changed(c)) { ctx.strokeStyle = "#50ff78"; ctx.lineWidth = 1 / Z; ctx.strokeRect(x, y, w, h); }
    if (marks || isSel) { ctx.fillStyle = isSel ? "#50e0ff" : changed(c) ? "#50ff78" : "#f0c060"; ctx.beginPath(); ctx.arc(c.u, c.v, 2.2, 0, 7); ctx.fill(); }
  }
  info();
}
function info() {
  const c = R && V && cards().find((c) => c.id === sel);
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
  const [dx, dy] = solve2(du, dv);
  push(); setFoot(c, [c.foot[0] + dx, c.foot[1] + dy, c.foot[2] + dz]); dirty(); draw();
}
function pt(e) { const b = cv.getBoundingClientRect(); return [(e.clientX - b.left) / Z, (e.clientY - b.top) / Z]; }
function hits(p) {
  return cards().filter((c) => { const [x, y, w, h] = rect(c); return p[0] >= x && p[0] < x + w && p[1] >= y && p[1] < y + h; })
    .sort((a, b) => a.depth - b.depth);                            // nearest to the camera first
}
function ground(p) {                                               // editor point -> the nearest cell surface along the view ray (a card origin there)
  const top = {}; for (const [x, y, h] of R.cells) top[x + "," + y] = h;
  const hs = [...new Set(R.cells.map((c) => c[2]))];
  const A = V.A; let best = null;
  for (const z of hs) {
    const [x, y] = solve2(p[0] - A[0][2] * z - A[0][3], p[1] - A[1][2] * z - A[1][3]);
    if (top[Math.floor((x - R.O) / 16) + "," + Math.floor((y - R.O) / 16)] !== z) continue;
    const d = proj([x, y, z])[2];
    if (!best || d < best[3]) best = [x, y, z, d];
  }
  if (!best) { const [x, y] = solve2(p[0] - A[0][3], p[1] - A[1][3]); best = [x, y, 0]; }
  const o = V.name === "game" ? [0, 0, 0] : [-7.5, -7.5, 0];      // the clicked point is the card's origin; the foot lies by the view's card offset
  return [r2(best[0] - o[0]), r2(best[1] - o[1]), best[2]];
}

cv.addEventListener("mousedown", (e) => {
  if (!R || !V) return; const p = pt(e);
  if (placing) { push(); const f = ground(p); edits.add.push({ kind: placing, x: f[0], y: f[1], z: f[2] }); sel = "add:" + (edits.add.length - 1); placing = null; dirty(); draw(); return; }
  const h = hits(p);
  if (!h.length) { sel = null; draw(); return; }
  const key = h.map((c) => c.id).join("|");
  let c = h[0];
  if (cycle.key === key && h.some((x) => x.id === sel)) {        // clicked the same stack again: the next sprite behind
    c = cycle.moved ? h.find((x) => x.id === sel) : h[(h.findIndex((x) => x.id === sel) + 1) % h.length];
  }
  cycle = { key, moved: false };
  sel = c.id; drag = { p, foot: c.foot.slice(), pushed: false }; draw();
});
window.addEventListener("mousemove", (e) => {
  if (!drag) return; const p = pt(e); const du = p[0] - drag.p[0], dv = p[1] - drag.p[1];
  if (!drag.pushed && Math.abs(du) + Math.abs(dv) < 1.5) return;
  const c = cards().find((c) => c.id === sel); if (!c || c.deleted) return;
  if (!drag.pushed) { push(); drag.pushed = true; cycle.moved = true; }
  const [dx, dy] = solve2(du, dv);
  setFoot(c, [drag.foot[0] + dx, drag.foot[1] + dy, drag.foot[2]]); dirty(); draw();
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
  if (e.key === "f" || e.key === "F") toggleFinished();
  if (e.key === "q" || e.key === "Q") turn(-1);
  if (e.key === "e" || e.key === "E") turn(1);
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
function toggleFinished() { finished = !finished; $("finished").classList.toggle("on", finished); showBg(); draw(); }
function showBg() {
  const game = V.name === "game"; loadMask(V); loadHd(V);
  $("bgo").style.display = game ? "" : "none";
  $("fadebox").style.visibility = game ? "visible" : "hidden";
  $("bgr").src = "/img/" + (finished ? (game ? "game.png" : V.name + ".png") : V.img) + "?t=" + stamp;
  $("bgr").style.opacity = game ? $("fade").value / 100 : 1;
}
function setView(name) {
  const v = R && R.views.find((x) => x.name === name); if (!v) return;
  const view = $("view"); const cx = (view.scrollLeft + view.clientWidth / 2) / Z / V.w, cy = (view.scrollTop + view.clientHeight / 2) / Z / V.h;
  V = v; for (const b of document.querySelectorAll(".vbtn")) b.classList.toggle("on", b.dataset.v === name);
  showBg(); zoom(Z);
  view.scrollTo(cx * V.w * Z - view.clientWidth / 2, cy * V.h * Z - view.clientHeight / 2);
}
function turn(d) { const n = ["game", "q1", "q2", "q3"]; setView(n[(n.indexOf(V.name) + d + 4) % 4]); }
async function save() {
  const r = await fetch("/api/save", { method: "POST", body: JSON.stringify(edits) });
  if (r.ok) { saved = JSON.stringify(edits); dirty(); } else status("Speichern fehlgeschlagen");
}
async function render() {
  await fetch("/api/render", { method: "POST", body: JSON.stringify(edits) }); $("render").disabled = true;   // renders the current edits WITHOUT saving them
  const t0 = Date.now();
  const poll = async () => {
    const s = await (await fetch("/api/render")).json();
    if (s.state === "running") { status("rendert ... " + Math.round((Date.now() - t0) / 1000) + " s (dauert etwa 1-2 Minuten)"); setTimeout(poll, 2000); return; }
    $("render").disabled = false;
    if (s.state === "failed") { status("Rendern fehlgeschlagen (Meldung im Konsole-Fenster)"); console.log(s.log); return; }
    await load(true); status("gerendert in " + Math.round(s.took) + " s" + (JSON.stringify(edits) === saved ? "" : " · nicht gespeichert"));
  };
  poll();
}
function zoom(z) {
  Z = Math.max(1, Math.min(6, z)); $("zv").textContent = Z + "x"; if (!V) return;
  for (const i of [$("bgo"), $("bgr")]) { i.style.width = V.w * Z + "px"; i.style.height = V.h * Z + "px"; }
  $("stage").style.width = V.w * Z + "px"; $("stage").style.height = V.h * Z + "px"; draw();
}
async function load(keep) {                                         // keep = after 'Rendern': the page's edits stay (they may be unsaved)
  const r = await fetch("/api/room");
  if (!r.ok) { status("Noch kein Render da: bitte 'Rendern' drücken"); R = null; return; }
  R = await r.json(); const ov = R.overrides || {};
  if (!R.views) {                                                  // a render from before the views: game view only, until 'Rendern'
    R.views = [{ name: "game", img: "game.png", w: 1056, h: 912, s: 1, offs: {}, A: [[1, -1, 0, 1184 - R.window[0]], [0.5, 0.5, -1, -R.window[1]], [-1, -1, -1, 0]] }];
    status("Bitte einmal 'Rendern' drücken (neue Ansichten)");
  }
  const fromFile = { move: Object.assign({}, ov.move || {}), delete: (ov.delete || []).slice(), add: (ov.add || []).map((a) => Object.assign({}, a)) };
  saved = JSON.stringify(fromFile);
  if (!keep) { edits = fromFile; undo = []; }
  stamp = String(R.render_time); for (const k in masks) delete masks[k]; for (const k in hds) delete hds[k];
  $("room").textContent = "Raum " + R.room + " · " + R.cards.length + " Sprites";
  $("bgo").src = "/img/original.png";
  const k = $("kinds"); k.innerHTML = "";
  for (const name of R.kinds) {
    const b = document.createElement("button"); b.innerHTML = '<img src="/props/' + name + '.png" alt=""><span>' + name + "</span>";
    b.onclick = () => { placing = name; sel = null; draw(); }; k.appendChild(b);
  }
  const first = !V; V = R.views.find((v) => v.name === (V ? V.name : (location.hash.slice(1) || "game"))) || R.views[0];   // #q1 .. #q3 opens a turned view
  for (const b of document.querySelectorAll(".vbtn")) b.classList.toggle("on", b.dataset.v === V.name);
  showBg(); zoom(Z); if (R.views.length > 1) dirty();
  if (first) { const v = $("view"); v.scrollTo(560 * Z - v.clientWidth / 2, 450 * Z - v.clientHeight / 2); }   // start on the village
}
$("fade").oninput = () => { if (V && V.name === "game") $("bgr").style.opacity = $("fade").value / 100; };
$("zin").onclick = () => zoom(Z + 1); $("zout").onclick = () => zoom(Z - 1);
$("view").addEventListener("wheel", (e) => { if (e.ctrlKey) { e.preventDefault(); zoom(Z + (e.deltaY < 0 ? 1 : -1)); } }, { passive: false });
for (const b of document.querySelectorAll(".vbtn")) b.onclick = () => setView(b.dataset.v);
$("marks").onclick = toggleMarks; $("finished").onclick = toggleFinished; $("undo").onclick = doUndo; $("save").onclick = save; $("render").onclick = render;
$("del").onclick = del; $("up").onclick = () => nudge(0, 0, 1); $("down").onclick = () => nudge(0, 0, -1);
$("discard").onclick = () => { if (JSON.stringify(edits) === saved) return; if (!confirm("Alle nicht gespeicherten Änderungen verwerfen?")) return; push(); edits = JSON.parse(saved); sel = null; dirty(); draw(); };
$("reset").onclick = () => { const c = cards().find((c) => c.id === sel); if (!c || c.added) return; push(); delete edits.move[c.id]; edits.delete = edits.delete.filter((x) => x !== c.id); dirty(); draw(); };
window.addEventListener("beforeunload", (e) => { if (JSON.stringify(edits) !== saved) { e.preventDefault(); e.returnValue = ""; } });
load();
