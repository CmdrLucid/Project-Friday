# Armour knight (Mercator houses, tileset 2) - light shape + remake model, work in progress since 2026-11-11

Recipe only (no ROM data). Reference: room 678 cell (30, 26); `remake/tools/rom_picture.py ROM 678 1216 392 64 80 DIR`; the knight's own pixels =
the layer A component at the breastplate, black pixels only next to a coloured one (the black blob under the feet is a painted shadow) -> a local
`mask678.json` (never in git). Cells: top block $19C (678 679: 30 / 33, 26; 695 696 697 719 720: 34, 23) and $2D7 (695 696 697 719 720: 23, 23), all the
same drawing. The castle's dark armour on a stand (tileset 15, $0B5: 63 64 83 84 93) is ANOTHER object (no legs, a pole with a round foot): later.

- `knight.py OUT.obj [params.json]`: the figure from parts in pure Python (ellipsoids, tapered capsules, lathes, a bent plate): sabatons, greaves, knee
  cops, cuisses, fauld, breastplate, collar, great helm + crest, pauldrons, arms, gauntlet on the lance, lance (shaft, tassel, leaf head), kite shield.
  The lance and the shield are placed by their measured room offsets from the cell centre; the body by `body`, `yaw` (legs), `twist` (upper body), `splay`.
- `chk.py OBJ MASK.json U0 V0`: projection check + character map. Exact game view beside the sprite: `../church_angel_sculpt/gameview.py` with
  GV_U0 1216 GV_V0 392 GV_W 64 GV_H 80.
- v1 (2026-11-11): blockout, IoU 0.824 (71 px outside, 108 missed), yaw 0 (it faces +y, out of the wall), twist 25, feet turned out 22. Read from the
  fit: the drawing follows the sprite convention (level shoulders, feet pointing in two directions), so no single facing fits everything.
  Preview `~/.landstalker_remake/assets/knight/knight_v1.png`. Waiting for the user's look before the details (plates, visor, hands, shield rim).
- v2 / v3 (2026-11-11, user 'ja', then 'diese 2 vertikalen Linien sind noch komisch'): plate-armour details (pointed sabatons, shin ridges, winged knee
  cops, fauld of three hoops, belt, collar, helm with brow rim and eye-slit ledge, ONE plume falling to the side, pauldron lames, couters, gauntlet cuff +
  fist, lance with butt / tassel tufts / socket / leaf head, shield with a raised rim); the stuck-on keel and nasal ridge removed. The feet point in two
  directions as drawn (`splay_r` 45, `splay_l` 30). IoU 0.817 (71 outside, 115 missed), ~10000 faces.
- IN THE LIGHT since 2026-11-11: `remake/tools/furniture_ops.py` knights() / knight_obj() -> `data/proxies/knight_ROOM[_k].obj` (14 knights, 7 rooms).
  A wall block west / east of the cell: `xmin` / `xmax` -> the lance / shield SLIDE ALONG THE VIEW RAY to the cell's edge (same game picture, nothing
  inside the wall). 678 is not reachable by warp (black); checked in 695 (`695:27.08,27.08,0010`): no boxes or cut walls; edge pixels at the corner
  knight 415 -> 563 (shading on the figure where the model and the drawing differ), whole picture 3699 -> 3826.

- v4 (2026-11-11, user: 'das sieht mir noch nicht nach einem Helm mit Visier aus'): `visor()` = a plate of its own over the face (a pointed snout, its
  upper edge under the eye slit, round pivots at the temples), a low comb, ONE smooth plume (capsule chain). IoU 0.821. Proxies rewritten, game rebuilt.
- v5 (2026-11-11, user: 'der Visierschlitz geht im Modell rundum statt nur bei der Augenpartie wie im Sprite'): the helm's skull is smooth all around;
  the eye slit is a sunk band in the visor's front only (+-52 degrees, `visor(slit=, slit_half=)`), a brow plate above it. Proxies rewritten, rebuilt.
- v6 (2026-11-11, user: 'oben am Helm sind es Federn ... im Sprite 2 Stueck'): `feather()` = a thin curved blade (quill, vane, shaft ridge, cupped, its flat
  side to the game camera; assumes yaw 0); TWO feathers: a short upright one at the front, a long one sweeping to the figure's left / back. IoU ~0.82.
- v7 (2026-11-11, user: 'die 2 Federn aus demselben Ursprungspunkt ... detaillierter, dann done') = FINISHED for now: both feathers grow from one holder
  on the helm's top (`feather_base`); `feather()` with BARBS (herringbone ridges on both faces), a finely scalloped edge and a few SPLITS in the vane;
  the low comb removed (only its ends showed as nubs). ~16000 faces, IoU 0.823 (66 outside, 113 missed). Rebuilt; 695: edge pixels at the corner knight
  415 (no knight shape) -> 608, right knight 386 -> 413, whole picture 3699 -> 3937 (shading on the figures; no boxes / cut walls seen). Not played.
  Export (not in git): `~/.landstalker_remake/assets/knight/knight_v7.obj`, sheet `knight_v7.png`.

## Armour on a stand (castle, tileset 15) - `stand.py`
- Game: top block $0B5, blocked cells: rooms 63 64 (19, 25 / 28 / 31; floor 2 = z 32), 83 84 (15, 21 / 24 / 27; floor 1), 93 (30, 27). Reference: room 63
  cell (19, 28), `rom_picture.py ROM 63 1008 280 72 110 DIR`, the armour's layer A component = `mask63.json` (local).
- `stand.py OUT.obj [params.json]` reuses the part makers of knight.py (everything above '# ---- the figure', incl. `visor()`): stepped round foot (radius
  6.7, exactly on the cell centre), pole, fauld of three hoops + two tassets, breastplate with a round boss, collar, round helm with a visor, ball
  pauldrons, hanging arms with gauntlets. It faces +x (out of the west wall), yaw 79 (11 degrees towards the camera, from the line through the pauldrons).
- v1 (2026-11-11): IoU 0.896 (33 outside, 66 missed). As DRAWN the armour sits 1.9 off the pole's axis, the near pauldron is big and high (r 4.0), the
  far one small (r 2.9), the far arm shorter: fitted so; from the front the model is lopsided. Open (user): keep as drawn, or a symmetric remake variant
  + this one for the light (as with the angel's wings). Not in the light yet. Preview `~/.landstalker_remake/assets/armour_stand/stand_v1.png`.
- v2 (2026-11-11, user: 'richtig in 3D bauen fuers Remake, die kleinere Schulter ergibt sich im echten 3D Modell durch die Perspektive', 'die Platten
  unten sind noch nicht gut', 'der Staender ist aus der Spielperspektive kaum zu erkennen'): SYMMETRIC and centred on the pole (equal pauldrons r 3.7,
  equal arms; in the game view the helm hides part of the far pauldron); the fauld = a bell of three stepped lames ending at z 12.8, two pointed TASSETS
  at the hips (`plate()`, turned 40 degrees outwards) so the front stays open; the stand = a thicker pole with a turned collar and a taller stepped foot,
  visible between the tassets from the game camera. IoU 0.789 (98 outside, 117 missed: the drawing has the armour ~2 px off the pole and unequal
  shoulders). Preview `stand_v2.png`. Not in the light yet.
- v3 (2026-11-11, user: 'Schultern sitzen zu hoch fuers 3D Remake Modell, sonst passts, oder Kopf zu niedrig'): pauldrons at z 26.9 (was 29.8), the helm
  0.9 higher on a taller collar. IoU 0.780. IN THE LIGHT: `furniture_ops.py` armour_stands() / stand_obj() -> `data/proxies/stand_ROOM[_k].obj`, 12 stands
  in 63 64 83 84 (all pixel-identical to 63 cell 19, 28; walls west / north / south -> xmin / ymin / ymax, parts slide along the view ray; room 93 left
  out: height 0 in a void height map). Built; headless before / after: 63 (`63:26.08,26.08,0020`) edge pixels 3921 -> 4056, 83 (`83:21.08,22.08,0010`)
  608 -> 1000 (shading on the armours, they are darker than the lit block before; no boxes / cut walls seen). Not played.
