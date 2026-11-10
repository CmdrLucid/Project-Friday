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
