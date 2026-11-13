# CPU light removal: inventory and plan (2026-11-12)

User decision 2026-11-12: remove the CPU per-pixel light; only the GPU light stays, without GPU support Lighting is simply Off (original picture).
HANDOFF NEXT -177. Start AFTER the user tested the 2026-11-12 build. Until then: no CPU light fixes, judge lighting only by GPU pictures.

Inventory: read-only survey by a Sonnet Explore agent, spot-checked by the lead (odcap coupling, patch_gpucomp lk_lt_block call, the
patch_bootcol / patch_dissolve anchors: confirmed). Line numbers = lines in the Python generator files on dev b806445, [L] = tools/patch_lights.py,
[G] = tools/patch_gpulight.py; they drift, re-grep before editing. Nothing here is verified by a build.

## 0. Progress
- 2026-11-12 late: steps 1, 2 (behaviour: GPULT gone, lk_gl_put gone; compare pass / GL5CMP code still there, dead), 3 (behaviour: GL5 unavailable / slow -> lk_gl_slow = Lighting off; GL4 upload code dead), 4 (done) and 6 (row removed; lk_gle_get() returns 1) DONE, commits bd39a5c / d9ab321 / 3efc06b. Open: 5, the dead code of 2 / 3, 7. Baselines ~/lktest/cpurm.

- 2026-11-12 night: steps 5 and 7 DONE (f594a01): ALL STEPS DONE. Found on the way: thread-local lk_lt_rayA had to default to 1 (it was set by the first CPU block). This file is history now.

## 1. How GPU vs CPU is decided today
- Master switch `lk_lt_get()` [L186] (Options Lighting, LANDSTALKER_LIGHTING, ~/.landstalker_lighting). Off = original picture.
- Option Renderer (id 56, patch_options.py) -> `lk_gle_get()` [G66] (~/.landstalker_lightengine, LANDSTALKER_LIGHTENGINE, default GPU). ALSO drives the
  GPU picture compositor (patch_gpucomp.py `lk_gco_get()` follows it): row 56 stays, only its light meaning goes.
- `lk_gl_getmode()` [G79]: LANDSTALKER_GPULT (0 CPU, 1 GPU, 2 compare), else GPU if `lk_gle_get() && !lk_gl_slow`; `lk_gl_slow` = 6 ms light-pass watchdog [G1143] -> CPU light for the rest of the run.
- Per line in vdp_render.c [G300]: `lk_gl_real` (capture on, mode 1, `lk_gl_realok()` = `lk_gpu_lightok`) -> `lk_gl_classify`; else `lk_lt_pix` / `lk_lt_voidglow` (= the CPU light).
- GL5 (`lk_g5_realon` [G1478]) default on; LANDSTALKER_GL5=0 or the 5 ms block watchdog [G1466] = 'GL4 path' (GPU light pass with CPU blocks `lk_lt_b`).
- While GL5 runs the CPU computes no blocks (`lk_gl5_cpuoff()` [G286]); LANDSTALKER_GL5_CPUKEEP keeps it computing (test aid).
- No GPU today (headless, GL init fail, filters off, Renderer = CPU, watchdog): full CPU path.
- HIDDEN COUPLING: shader uniform uOd0 = `iu[6] = lk_lt_odcap == 0` [G115] switches the GPU's flat base light for blocks not computed yet;
  `lk_lt_odcap` is 0 only after the CPU worker threads started [L946]. Without workers the GPU base light is off. After removal: iu[6] = 1 always.

## 2. CPU only (to remove)
- Compositing: `lk_lt_pix` [L2096-2209], `lk_lt_voidglow` [L2085], `lk_lt_linebegin` [L2082], `lk_lt_amb` (also read by `lk_gl_frame` fu[0]: check), `lk_lt_term` [L676-716],
  figure shading `lk_lt_shadowed` / `lk_lt_figdir` / `lk_lt_figface` [L2033-2075].
- Blocks: `lk_lt_blockcalc` [L847], `lk_lt_block` [L895], `lk_lt_sunfill` [L827], `lk_lt_shblock` [L510], `lk_lt_aoval` + aoh / aoh2 / aoenv / aoopt [L405-443], cache `lk_lt_b` / `lk_lt_blk` [L194].
- Workers [L906-949]: jobrun / worker / mtopt / jobwait / jobstart, LK_LT_NTH; `lk_lt_odcap` / odn / pre / bn / pfn / bms / pms [L256]; prefetch ring in `lk_lt_step` (~L1963), jobwait in step / newroom / free.
- GPU side helpers of the CPU blocks: `lk_gl_bver` / bsg / bpack / blist [G242-254], `lk_gl_put` + unlit / ref / cls / flg [G62, 85-91], compare branch [G306], pf flags [G311],
  `lk_gl5_cpuoff`, the CPU-block upload loop in `lk_glt_pass` [G1661], compare `lk_glt_pass(0)` + statistics [G1650-1738], GL5CMP (`lk_g5_want` / queue / run [G1212-1465]), GL5=0 / CPUKEEP / GPULT 0 / 2, `lk_gl_slow`.

## 3. CPU code the GPU still needs (keep)
- Room data prep `lk_lt_newroom` [L1516-1795] + helpers (heights top / thin / gh / vw / wat / hd, horizon, extrude, finebuild = fine field + slabs + halo,
  objbuild / roombuild, proxies, MESH loading, corr table), uploaded by `lk_gl_world` [G138], wkey, blist5, shafts.
- `lk_lt_ray` / rayf / rayi [L323-395] (light placement in newroom), `lk_lt_sunvis`, `lk_lt_keyvis(d)` (figure sun share -> GPU fg[3]).
- `lk_lt_step` minus the prefetch: room change, fade, day / night, flicker, sword glow, figures (+ fmkbuild / infb / figat / figsun), dust motes `lk_lt_shstep`,
  shaft setup, window lights, ambient particles `lk_am_*` (`lk_am_surf` keeps only the `lk_gs` GPU read-back branch; the PBO read-back stays).
- vdp_render hooks of the GPU path (classify, postset, frame, pairs, clstag, fmk, motes, unpaint: LK_GLUNPAINT must keep the original tiles when light is off / no GPU).
- `lk_lt_umin..vmax` (drawn area -> GL5 ring); patch_gpucomp.py:124 calls `lk_lt_block` per block: drop the call, keep the area updates.
- GL5 passes (real, prep, swap, LK_GL5RING, LK_GL5ENTRY).
- Other patches use `lk_lt_spre` / spre2 (dissolve, water, bootcol, gpucomp): keep. patch_bootcol.py:210 and patch_dissolve.py:82 anchor on the exact
  `lk_lt_pix` / `lk_lt_linebegin` lines: edit them in the same step. patch_shaderwarm.py uses `lk_lt_get()`, patch_options.py `lk_gle_get` / `lk_lt_get`.

## 4. Test aids
- CPU light today: headless runs (`--headless` + LANDSTALKER_SHOT = no GL): tools/lightshots.sh, tools/lightedges.py default mode, patch_shot.py (after removal: original picture),
  tools/gpucmp.sh (GPULT=2 / GL5CMP: dies with the CPU light). Probably data only, stay: tools/proxysurvey.py, tools/lightsurvey.py.
- Already GPU: tools/lightedges.py --gpu (hidden window, LANDSTALKER_PRESENT_SHOT -> present_FRAME_gpu.png). lightshots.sh needs a GPU mode first.
- tools/verify_build.sh greps the markers 'LK_LIGHTS v8' / 'LK_GPULT v5': keep the strings or edit the script.

## 5. Order (after every step: build, tools/lightedges.py --gpu on a fixed room set, present_*_gpu.png pixel identical to the step-0 pictures)
0. Baseline GPU pictures (outdoor, torch, key light, shaft, particle, water, ship rooms) before touching anything; GPU mode for lightshots.sh; lightedges default --gpu.
1. Remove the hidden coupling: iu[6] = 1 always (uOd0 constant). Pictures identical.
2. Remove the compare harness (GPULT=2, lk_gl_put / unlit / ref / flg, lk_glt_pass(0) + statistics, GL5CMP, gpucmp.sh).
3. Remove GL5=0, GL5_CPUKEEP, the lk_g5_slow fallback to CPU blocks (DECIDED, user 2026-11-12: 'wenn GPU-Licht nicht geht, dann wird standardmaessig das Licht aus' = slow / unavailable GPU light -> Lighting Off) and the GL4 CPU-block upload (bver / bpack / blist / bsg).
4. vdp_render: no `lk_lt_pix` / `lk_lt_voidglow` else-branch; `lk_gl_real` = lighting on && GPU ok; no GPU = rows untouched. Delete lk_lt_pix, voidglow, term,
   shadowed / figdir / figface; adjust the patch_bootcol / patch_dissolve anchors in the same step.
5. Remove prefetch ring, on-demand lk_lt_block, workers; delete blockcalc, sunfill, shblock, aoval / aoh, lk_lt_b; patch_gpucomp drops lk_lt_block; lk_am_surf only via lk_gs.
6. REMOVE the Options row 'Renderer' (Display page, id 56 in tools/patch_options.py lk_ids_video; it sets the Light Engine AND the Picture Engine, value text CPU / GPU at the
   `id == 56 || id == 60` line; files ~/.landstalker_lightengine, LANDSTALKER_LIGHTENGINE) - user 2026-11-12: 'die Option im Optionsmenue weggeben, weil es die dann ohnehin nicht mehr gibt'.
   The picture compositor (patch_gpucomp.py `lk_gco_get()` follows `lk_gle_get()`) then decides by itself: GPU when the GPU works, else the plain picture path (no choice row).
   Light = `lk_lt_get() && lk_gpu_lightok()`; the 6 ms watchdog turns the light OFF (decided, step 3). Also: the row's help text, LANG translations (tools/lang*), docs/options lists,
   the id 60 name, and keep the other ids of the page unchanged (saved option files use the ids).
7. Dead statics, verify_build.sh markers, docs (INDEX, LESSONS, FORMATS, options help text), re-run the baseline.
