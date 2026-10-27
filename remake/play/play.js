// Massan walk demo (user 2026-10-27: 'diese Karte spielbar machen', chosen: walk demo). Served by remake/tools/editor.py at /play.
// The room is drawn from the editor's per-view data (recipes/room_c.py: nocards_<view>.png background, mask_<view>.png houses, hd_<view>.png fences /
// terrain, cards.json projection + cards + cells); Nigel (tools/nigel_frames.py) walks on the height map with the original's 15 x 15 box and is
// covered by the same rules the editor / sort_cards use. No game logic of the original (no people, doors, fights): a look-and-feel test.
"use strict";
const $ = (id) => document.getElementById(id);
const cv = $("cv"), ctx = cv.getContext("2d");
let R = null, F = null, V = null, Z = 3;
const VIEWS = {};             // name -> {v, bg, masks: [canvas], hd: {w, h, hd}, cards: [{c, can, x, y, w, h, depth, o}], layer}
const fimg = {};
const N = { x: 0, y: 0, z: 0, vz: 0, dir: [0, 1], walk: 0, moving: false };
const cam = { x: 0, y: 0 };
const keys = {};
let pads = { turnL: false, turnR: false, jump: false };

function loadImg(src) { return new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => no(src); i.src = src; }); }
function proj(A, g) { return [0, 1, 2].map((i) => A[i][0] * g[0] + A[i][1] * g[1] + A[i][2] * g[2] + A[i][3]); }
function solve2(A, du, dv) { const a = A[0][0], b = A[0][1], c = A[1][0], d = A[1][1], det = a * d - b * c; return [(d * du - b * dv) / det, (-c * du + a * dv) / det]; }

// ---- covering (the same rules as remake/editor/editor.js) -------------------------------------------------------------------------------------------
function side(v, F_, b) {
  const m = 1, vx = v.A[2][0], vy = v.A[2][1];
  if (F_[0] > b[0] + m && F_[0] < b[1] - m && F_[1] > b[2] + m && F_[1] < b[3] - m) return -1;
  const fx = vx > 1e-6 ? F_[0] <= b[0] + m : vx < -1e-6 ? F_[0] >= b[1] - m : false, fy = vy > 1e-6 ? F_[1] <= b[2] + m : vy < -1e-6 ? F_[1] >= b[3] - m : false;
  const bx = vx > 1e-6 ? F_[0] >= b[1] - m : vx < -1e-6 ? F_[0] <= b[0] + m : false, by = vy > 1e-6 ? F_[1] >= b[3] - m : vy < -1e-6 ? F_[1] <= b[2] + m : false;
  if ((fx || fy) && !(bx || by)) return 1;
  if ((bx || by) && !(fx || fy)) return -1;
  return 0;
}
// a sprite (image, scale s) whose origin (bottom centre) is the game point o, drawn into its own canvas with every covered pixel removed
function covered(W, img, o, flip) {
  const v = W.v, p = proj(v.A, o), w = img.naturalWidth * v.s, h = img.naturalHeight * v.s;
  let x = p[0] - w / 2, y = p[1] - h; if (v.name === "game") { x = Math.floor(p[0] - 0.5 - w / 2); y = Math.round(p[1] - h); }
  const x0 = Math.floor(x), y0 = Math.floor(y), CW = Math.ceil(w) + 2, CH = Math.ceil(h) + 2;
  const c = document.createElement("canvas"); c.width = CW; c.height = CH; const g = c.getContext("2d", { willReadFrequently: true }); g.imageSmoothingEnabled = false;
  if (flip) { g.save(); g.translate(x - x0 + w, y - y0); g.scale(-1, 1); g.drawImage(img, 0, 0, w, h); g.restore(); }
  else g.drawImage(img, x - x0, y - y0, w, h);
  g.globalCompositeOperation = "destination-out";
  R.houses.forEach((b, k) => { if (W.masks && side(v, o, b) < 0) g.drawImage(W.masks[k], -x0, -y0, v.w, v.h); });
  g.globalCompositeOperation = "source-over";
  if (W.hd) {
    const fh = o[0] * v.hv[0] + o[1] * v.hv[1] - 2, im = g.getImageData(0, 0, CW, CH), d = im.data; let hit = false;
    for (let j = 0; j < CH; j++) {
      const yy = y0 + j; if (yy < 0 || yy >= W.hd.h) continue;
      for (let i = 0; i < CW; i++) {
        const xx = x0 + i; if (xx < 0 || xx >= W.hd.w || !d[(j * CW + i) * 4 + 3]) continue;
        if (W.hd.hd[yy * W.hd.w + xx] < fh) { d[(j * CW + i) * 4 + 3] = 0; hit = true; }
      }
    }
    if (hit) g.putImageData(im, 0, 0);
  }
  return { can: c, x: x0, y: y0, w: CW, h: CH, depth: p[2] };
}
async function loadView(v) {
  const W = { v };
  const [bg, mk, hdI] = await Promise.all([loadImg("/img/" + v.img), loadImg("/img/" + v.mask), loadImg("/img/" + v.hd)]);
  W.bg = bg;
  { const w = mk.naturalWidth, h = mk.naturalHeight, c0 = document.createElement("canvas"); c0.width = w; c0.height = h; const g = c0.getContext("2d"); g.drawImage(mk, 0, 0);
    const src = g.getImageData(0, 0, w, h).data;
    W.masks = R.houses.map((_, k) => { const c = document.createElement("canvas"); c.width = w; c.height = h; const gc = c.getContext("2d"); const d = gc.createImageData(w, h);
      for (let p = 0; p < w * h; p++) if (src[p * 4 + 3] > 128 && Math.round(src[p * 4] / R.house_step) === k + 1) d.data[p * 4 + 3] = 255;
      gc.putImageData(d, 0, 0); return c; }); }
  { const w = hdI.naturalWidth, h = hdI.naturalHeight, c0 = document.createElement("canvas"); c0.width = w; c0.height = h; const g = c0.getContext("2d"); g.drawImage(hdI, 0, 0);
    const d = g.getImageData(0, 0, w, h).data, hd = new Float32Array(w * h);
    for (let p = 0; p < w * h; p++) {
      if (d[p * 4 + 3] < 128) { hd[p] = NaN; continue; }
      const t = d[p * 4] / 255, f = d[p * 4 + 1] / 255; let tf = (Math.round(t * 16 - f) + f) / 16; if (Math.abs(tf - t) > 1.5 / 255) tf = t;
      hd[p] = v.hd_lo + tf * (v.hd_hi - v.hd_lo);
    }
    W.hd = { w, h, hd }; }
  // the static cards (pines, bushes, statue), each cut by what covers it, and one layer of all of them (far first)
  W.cards = [];
  for (const c of R.cards) {
    if (c.deleted || !c.img) continue;
    const i = await loadImg("/props/" + c.img); const off = (v.offs && v.offs[c.id]) || [0, 0, 0];
    const o = [c.foot[0] + off[0], c.foot[1] + off[1], c.foot[2] + off[2]];
    W.cards.push(Object.assign(covered(W, i, o, false), { o }));
  }
  W.cards.sort((a, b) => b.depth - a.depth);
  W.layer = document.createElement("canvas"); W.layer.width = Math.ceil(v.w); W.layer.height = Math.ceil(v.h);
  const lg = W.layer.getContext("2d"); for (const k of W.cards) lg.drawImage(k.can, k.x, k.y);
  VIEWS[v.name] = W;
}

// ---- walking on the height map ---------------------------------------------------------------------------------------------------------------------
const CELLS = {};
function cell(x, y) { return CELLS[Math.floor((x - R.O) / 16) + "," + Math.floor((y - R.O) / 16)]; }
function groundAt(x, y, z, climb) {                                // highest walk height under the 15 x 15 box, or null if a corner is blocked / too high
  let g = -1e9;
  for (const [dx, dy] of [[-7, -7], [7, -7], [-7, 7], [7, 7]]) {
    const c = cell(x + dx, y + dy);
    if (!c || c.blk || c.h > z + climb + 0.01) return null;
    g = Math.max(g, c.h);
  }
  return g;
}
function dirs() {                                                  // world direction for each pad direction in this view (camera relative)
  const want = { up: [1, -1], right: [1, 1], down: [-1, 1], left: [-1, -1] }, out = {};
  for (const k in want) {
    let best = null;
    for (const d of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const p = proj(V.v.A, [d[0], d[1], 0]), p0 = proj(V.v.A, [0, 0, 0]); const du = p[0] - p0[0], dv = p[1] - p0[1], l = Math.hypot(du, dv);
      const sc = (du * want[k][0] + dv * want[k][1]) / l; if (!best || sc > best[0]) best = [sc, d];
    }
    out[k] = best[1];
  }
  return out;
}
function input() {
  const k = (a) => a.some((x) => keys[x]);
  let up = k(["ArrowUp", "w", "W"]), down = k(["ArrowDown", "s", "S"]), left = k(["ArrowLeft", "a", "A"]), right = k(["ArrowRight", "d", "D"]);
  let jump = k([" ", "Enter"]), tl = false, tr = false;
  for (const gp of navigator.getGamepads ? navigator.getGamepads() : []) {
    if (!gp) continue; const b = (i) => gp.buttons[i] && gp.buttons[i].pressed;
    up = up || b(12) || gp.axes[1] < -0.5; down = down || b(13) || gp.axes[1] > 0.5; left = left || b(14) || gp.axes[0] < -0.5; right = right || b(15) || gp.axes[0] > 0.5;
    jump = jump || b(0); tl = tl || b(4); tr = tr || b(5);
  }
  if (tl && !pads.turnL) turn(-1); if (tr && !pads.turnR) turn(1);
  pads.turnL = tl; pads.turnR = tr;
  return { up, down, left, right, jump };
}
function step() {
  const inp = input(), D = dirs(); let mx = 0, my = 0;
  for (const k of ["up", "down", "left", "right"]) if (inp[k]) { mx += D[k][0]; my += D[k][1]; }
  const l = Math.hypot(mx, my); const speed = 1.3;
  N.moving = l > 0;
  if (N.moving) {
    mx = mx / l * speed; my = my / l * speed; N.dir = [Math.sign(mx) * (Math.abs(mx) >= Math.abs(my) ? 1 : 0), Math.sign(my) * (Math.abs(my) > Math.abs(mx) ? 1 : 0)];
    const climb = N.vz === 0 ? 16 : 0;                             // one step up while walking, more only by jumping
    if (groundAt(N.x + mx, N.y, N.z, climb) !== null) N.x += mx;
    if (groundAt(N.x, N.y + my, N.z, climb) !== null) N.y += my;
    N.walk += 1;
  } else N.walk = 0;
  const g = groundAt(N.x, N.y, N.z, 16);
  if (inp.jump && N.z <= (g ?? N.z) + 0.01 && !N.jumpHeld) N.vz = 4.2;
  N.jumpHeld = inp.jump;
  if (g !== null && g > N.z && N.vz === 0) N.z = g;
  if (N.vz !== 0 || (g !== null && N.z > g)) { N.vz -= 0.32; N.z += N.vz; if (g !== null && N.z <= g) { N.z = g; N.vz = 0; } }
}

// ---- drawing --------------------------------------------------------------------------------------------------------------------------------------
function nigel() {                                                 // frame, flip, origin (front corner of the box towards the camera)
  const v = V.v, p0 = proj(v.A, [0, 0, 0]), p = proj(v.A, [N.dir[0], N.dir[1], 0]); const du = p[0] - p0[0], dv = p[1] - p0[1];
  const front = dv > 0, flip = front ? du > 0 : du < 0;
  const set = N.moving ? (front ? F.walk_front : F.walk_back) : (front ? F.stand_front : F.stand_back);
  const fr = set[Math.floor(N.walk / 6) % set.length];
  const o = [N.x - 7.5 * Math.sign(v.hv[0]), N.y - 7.5 * Math.sign(v.hv[1]), N.z];
  return { img: fimg[fr.img], flip, o };
}
function draw() {
  const W = VIEWS[V.v.name]; const v = V.v;
  const sw = cv.width, sh = cv.height;
  const t = proj(v.A, [N.x, N.y, N.z + 16]);
  cam.x += (t[0] - cam.x) * 0.2; cam.y += (t[1] - cam.y) * 0.2;
  const vw = sw / Z, vh = sh / Z;
  const cx = Math.max(vw / 2, Math.min(v.w - vw / 2, cam.x)), cy = Math.max(vh / 2, Math.min(v.h - vh / 2, cam.y));
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = "#000"; ctx.fillRect(0, 0, sw, sh);
  ctx.setTransform(Z, 0, 0, Z, Math.round((vw / 2 - cx) * Z), Math.round((vh / 2 - cy) * Z));
  ctx.imageSmoothingEnabled = true; ctx.drawImage(W.bg, 0, 0, v.w, v.h);
  // shadow on the ground under Nigel
  const g = groundAt(N.x, N.y, 1e9, 0) ?? N.z; const sp = proj(v.A, [N.x, N.y, g]);
  ctx.fillStyle = "rgba(0,0,0,0.33)"; ctx.beginPath(); ctx.ellipse(sp[0], sp[1], 9 * v.s, 4.5 * v.s, 0, 0, 7); ctx.fill();
  ctx.imageSmoothingEnabled = false; ctx.drawImage(W.layer, 0, 0);
  const n = nigel(); if (!n.img) return;
  const s = covered(W, n.img, n.o, n.flip); ctx.drawImage(s.can, s.x, s.y);
  for (const k of W.cards) {                                       // cards in front of Nigel that overlap him are drawn again over him
    if (k.depth >= s.depth) continue;
    if (k.x > s.x + s.w || k.x + k.w < s.x || k.y > s.y + s.h || k.y + k.h < s.y) continue;
    ctx.drawImage(k.can, k.x, k.y);
  }
}
function turn(d) {
  const names = ["game", "q1", "q2", "q3"]; const v = R.views.find((x) => x.name === names[(names.indexOf(V.v.name) + d + 4) % 4]);
  V = { v }; const t = proj(v.A, [N.x, N.y, N.z + 16]); cam.x = t[0]; cam.y = t[1];
}
function resize() { cv.width = window.innerWidth; cv.height = window.innerHeight; }
let last = 0, acc = 0;
function loop(ts) {
  acc += Math.min(100, ts - (last || ts)); last = ts;
  while (acc >= 1000 / 60) { step(); acc -= 1000 / 60; }
  draw(); requestAnimationFrame(loop);
}
async function main() {
  resize(); window.addEventListener("resize", resize);
  R = await (await fetch("/api/room")).json();
  if (!R.views || !R.views[0].hd) { $("load").textContent = "Bitte im Editor einmal 'Rendern' drücken (neue Raumdaten fehlen)."; return; }
  for (const [x, y, top, h, blk] of R.cells) CELLS[x + "," + y] = { h: h ?? top, blk: !!blk };
  F = await (await fetch("/figures/nigel/frames.json")).json();
  for (const k in F) for (const f of F[k]) if (!fimg[f.img]) fimg[f.img] = await loadImg("/figures/nigel/" + f.img);
  let i = 0;
  for (const v of R.views) { $("load").textContent = "Lade Massan ... Ansicht " + (++i) + " / " + R.views.length; await loadView(v); }
  const st = R.start || [400, 400]; N.x = st[0]; N.y = st[1]; N.z = groundAt(N.x, N.y, 1e9, 0) ?? 0;
  V = { v: R.views[0] }; const t = proj(V.v.A, [N.x, N.y, N.z + 16]); cam.x = t[0]; cam.y = t[1];
  const sx = N.x + 24, sy = N.y + 24; const sg = groundAt(sx, sy, 1e9, 0); if (sg !== null) { N.x = sx; N.y = sy; N.z = sg; }   // a little in front of the statue
  // test aid: #hold=ArrowUp,ArrowRight&turn=1 holds keys / turns the camera (headless checks)
  const hp = new URLSearchParams(location.hash.slice(1));
  for (const k of (hp.get("hold") || "").split(",").filter(Boolean)) keys[k] = true;
  for (let i = 0; i < +(hp.get("turn") || 0); i++) turn(1);
  for (let i = 0; i < +(hp.get("steps") || 0); i++) step();       // &steps=N runs N frames of walking at once (headless browsers draw few frames)
  if (hp.get("steps")) { for (const k in keys) keys[k] = false; const t = proj(V.v.A, [N.x, N.y, N.z + 16]); cam.x = t[0]; cam.y = t[1]; document.title = "pos " + [N.x, N.y, N.z].map(Math.round).join(","); }
  $("load").remove(); requestAnimationFrame(loop);
}
window.addEventListener("keydown", (e) => {
  keys[e.key] = true;
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) e.preventDefault();
  if (e.key === "q" || e.key === "Q") turn(-1);
  if (e.key === "e" || e.key === "E") turn(1);
  if (e.key === "+") Z = Math.min(6, Z + 1);
  if (e.key === "-") Z = Math.max(1, Z - 1);
  if (e.key === "h" || e.key === "H") $("hud").style.display = $("hud").style.display === "none" ? "" : "none";
});
window.addEventListener("keyup", (e) => { keys[e.key] = false; });
window.addEventListener("blur", () => { for (const k in keys) keys[k] = false; });
$("tl").onclick = () => turn(-1); $("tr").onclick = () => turn(1);
$("zi").onclick = () => { Z = Math.min(6, Z + 1); }; $("zo").onclick = () => { Z = Math.max(1, Z - 1); };
$("fs").onclick = () => { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen(); };
main().catch((e) => { $("load").textContent = "Fehler beim Laden: " + e; });
