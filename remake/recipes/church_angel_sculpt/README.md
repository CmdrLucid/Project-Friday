# Church angel sculpt (near-final remake geometry, work in progress since 2026-11-10)

Recipe only (no ROM data): the statue's pixel mask `mask.json` and the reference picture are made locally from the user's ROM
(`~/lktest/angel3/mask.json`, `remake/tools/rom_picture.py ROM 613 1064 280 96 112 DIR`) and never go into git. The scripts still use the work
folder `~/lktest/sculpt/` (copy them there, or adjust the paths) and `/home/deck/lktest/pult2/chk.py` (projection helper) / `clay.py` (Blender preview).

Pipeline (`run.sh '{"robe_k": 0.7}'`, then `wing.py`, `post.py`, merge, `rend.sh`):
- `sculpt.py`: the BODY as Blender metaballs in game coordinates (robe = balls on the measured rings of `furniture.CHURCH_ANGEL4`, spiral fold grooves =
  negative capsules, torso, arms, child bundle, veiled head). Radii are SURFACE radii (a lone metaball shows its surface at 0.575 of its radius).
- `mb_blender.py`: Blender (Flatpak, `--filesystem=home`) turns the elements into a triangle OBJ (each group = its own metaball object with a unique name:
  metaballs whose names share a base merge).
- `post.py`: keeps the body inside the drawing along a SMOOTH outline (the pixel mask blurred, sigma 0.7 px, cut at 0.5); a vertex outside moves without
  depth change (dx = dU / 2, dy = -dU / 2, dz = -dV) up the field's gradient.
- `wing.py`: both wings as one clean mesh in the plane x = 371 (parallel to the niche's back wall), joined behind the body; thickness tapers to 0 at the
  smoothed outline; feathers = analytic relief (bands fanning out from each wing root, two staggered rows); thickness, relief and cup all ALONG THE VIEW
  RAY (1, 1, 1): the game picture stays exactly the drawn wing.
- `chk.py`: projection check against the mask (drawn / covered / outside / missed / IoU).

v11 (2026-11-11, user: 'neben dem Mund komisch geformt', then 'schau dir Haare, Gewand und Fluegel nochmal an'):
- `head.py` face: the base front profile carries NO lips (it made a shelf across the whole face at mouth height); the mouth sits on a local mound.
- `head.py` hair: long hair parted in the middle on its own finer grid (`h_nuh` 360): arch hairline, the sides fall beside the face to the jaw and sweep
  back behind the shoulders (curtain below `hair_hang`), strands = lines of constant Y from the parting; NOT clamped by post.py (it dented the strands;
  6 px outside at the crown).
- `robe.py` (new): the dress as ONE polygon lathe (spiral drapery folds, up over the torso into the shoulders; rows that would leave the drawn outline
  are squeezed smoothly); the metaball robe / torso are off (`robe_from` 25, `folds` 0, `torso` false); sloping shoulders, the neck blends in.
- `wing.py` feathers: a fan from the SHOULDER (`wr_a`, `wr_z`) in three rows (coverts, secondaries, primaries), each feather a shingle blade with a
  shaft and a rounded tip; rows follow the wing's reach per direction. Old version: git history.
- Close-ups: `fhead.sh TAG` (bare head), `hh.sh TAG` (head + hair), `up.sh`, `face.sh`. Check: IoU 0.831 (51 px outside, wings mirrored + hair).

v12 (2026-11-11, user: 'das Kind ist glaub ich eher eine Schriftrolle', goal: 'dem Sprite moeglichst aehnlich ... wie die Statue in einem 3D Remake
aussehen wuerde, so dass es auch fuers Licht stimmt'):
- `gameview.py` / `gv.sh TAG`: the model in the EXACT game projection (orthographic camera at 30 degrees elevation, the model's z scaled by sqrt(2 / 3),
  window = the sprite crop, 14 px per game pixel) beside and over the original sprite. Use it before every change: it showed the head was 8 px wide
  against 11.5 drawn, and that the drawing has NO child: a ring (shoulders, elbows, forearms / hands meeting in front) with a small bright-topped object.
- `scroll.py` (new): an upright scroll in both hands against the chest; `sculpt.py`: arms with elbows out, wide sleeves, hands (param `scroll`; false =
  the old child bundle).
- Head to the drawn size: `head_h` 8.4, `chin_z` 36.4, more hair volume, shoulders lower (`shoulder_z`, `trap_z`, `sh_z`), short neck.
- Bolder as drawn: 6 robe folds (`rfolds`, `rturn` 0.52), feathers in two rows, wider (`fan3` 0.3, `rows3`), the dress top closes as a dome.
- Check: IoU 0.830 (48 px outside, 165 missed: mostly the mirrored wings, the user's choice of 2026-11-10; open question whether to go back to the drawn wings).

v13 (2026-11-11, user: 'die Figur sieht aus, als waere sie nach vorn und zu den Fluegeln hin gedreht; die Fluegel muessen am Ruecken anliegen, parallel
zum Koerper', 'kein Loch ... eine komplette Form', 'eher verschraenkte Arme, in denen die Schriftrolle liegt'):
- `face_x` (all part scripts): the FIGURE FACES OUT OF THE WALL (+x), not the camera: the body frame is turned 45 degrees about the body's axis, so the
  wings (plane x = 371) lie on its back. Evidence in the drawing: both wings span the same heights in the wall plane (the left one is drawn lower only by
  the isometric view), and the arm ring sits 1 px right of the body's axis (as a front turned to +x gives).
- `wing.py` `complete` (with `mirror` false): each wing = its OWN drawn pixels (they are not mirror images in the drawing), completed: statue pixels
  between the two wings in the plane (hidden behind the body, z 57 .. 69.5) are filled = one piece across the back, notches closed; the feather fan
  starts at each shoulder blade (`wr_a` from the body's axis y = 449.25, `wr_z` 63), reach per side; depth along the plane normal. IoU 0.830 -> 0.898.
- `sculpt.py` `folded`: arms folded across the chest (hand at the other elbow), sleeves; `scroll.py`: the scroll lies diagonally in them.
- Open: forearms still lumpy, feathers flat in the game view's light, the face is mostly hidden from the game camera (hair + view from above).

v14 (2026-11-11, user marked a gap between the left wing and the body: 'so wuerde ein Fluegel nicht aussehen'; forearms 'zu knubbelig'; feathers):
- `fill_zlo` 50: the bridge across the back reaches down to the wings' lowest feathers (the body is narrower than the drawing at the waist: the wall
  showed through between wing and body). IoU 0.898 -> 0.922.
- The feather fan starts at the wing's TOP INNER corner (`wr_a` 1.5, `wr_z` 71): feathers hang down along the back, then turn outward to the tip, in
  three rows, a dark groove between two feathers (`groove`). A fan around the shoulder blade (v13) became a sunburst once the wing was complete.
- Arms: one even limb (no elbow / hand balls, no sleeve roll), a small flat hand.

v15 (2026-11-11, user: 'mit Gold und Licht sehen die Fluegel sehr dunkel aus, liegt das nur am Licht?'): YES, only the comparison render's light:
`gameview.py` lit from the picture's upper left (-55, 50), which is parallel to the wall plane = the wings got grazing light and the body's shadow. Now
lit from the front right (GV_SUN 25, 48): the feathers show like in the clay views. Also: forearms further apart with stiffer blending (no bulge where
they cross), wing grid 9 per pixel (`wgrid`, finer feather edges), stronger feathers (`feather_h` 1.3, `groove` 0.6), head upright (`head_tilt` 0,
`hl_front` 0.83: the face shows from the game camera). IoU 0.919.

v16 (2026-11-11, user: 'der rechte Fluegel wirkt chaotischer als der linke', 'die Schriftrolle liegt vor den Armen statt in den Armen'):
- Right wing: the head hides its inner top in the picture -> a notch with a loose lobe, and the feather fan's centre lay OUTSIDE the wing (reach 3 =
  broken rows). Now the bridge rises to the wings' full height from 1.5 to 6 units beside the body's axis (also over the dark outline pixels between
  head and wing: `mask1`), and the reach is the LAST wing point on each ray. Costs 21 px outside (IoU 0.919 -> 0.914): check before using it for the light.
- Scroll: axis at the chest (f 3.2 .. 4.0, r 0.9), the forearms further out (`ff_top` 5.2, `ff_low` 4.7): it lies between arms and chest.
