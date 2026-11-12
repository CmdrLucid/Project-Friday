# Grand piano (room 85) - light shape + remake model, since 2026-11-12

Recipe only (no ROM data). Reference: room 85 (MERCATOR_CASTLE_BANQUET_ROOM), `remake/tools/rom_picture.py ROM 85 970 180 170 170 DIR`.

- `piano.py OUT [params.json]`: the measured PLAN (`params_light.json`): `front` = stations (u, v) of the front edge read off the drawn bottom edge
  of the case (every bottom pixel at the case bottom z c0 = 7 inverts to one floor point: x - y = U - 1184, x + y = 2 (V + z)), smoothed by a
  Catmull-Rom curve; cx / cy / th = centre + turn of the long axis; c1 = 20 from the drawn side band; legs l1 / l2 = the drawn feet; kd / kz0 / kz1 /
  kv0 / kv1 = keyboard; su0 = the keyboard-end spine corner moved in; lid: lh (front edge above the rim), li (inset). Also writes the simple prism
  version (used by the silhouette fit).
- `model3d.py OUT [params.json]`: the NEAR-FINAL 3D model on that plan (case shell, iron plate, keys, turned legs, lid + prop stick), groups wood /
  brass / iron / keys; writes OUT_case.obj + OUT_lid.obj = `landstalker/data/proxies/piano_85_*.obj` (both ops `surface` + `air` in light_proxies.json).
- First try (night 2026-11-11/12, not kept): one Bezier front fitted on the silhouette only: lid too high and case too low cancelled out, the S sat
  wrong (user: 'die S-Kurve passt noch gar nicht'); and a solid case down to the floor ('viel zu tief runter', 'da ist nur Schatten drunter').
- The painted shadow (colour 5 dots in the piano's own plane A tiles) goes under the GPU light: op `unpaint` with `layer: a` (LK_GLUNPAINTA v1).
- Previews (local): `~/.landstalker_remake/assets/piano/piano_v1_clay.png`.
