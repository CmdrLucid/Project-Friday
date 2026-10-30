---
name: start
description: Starts a ProjectL/Project-Friday (Landstalker recomp + remake) work session - reads CLAUDE.md, the relevant parts of HANDOFF / LESSONS / INDEX, checks git and the Deck state, decides where Sonnet sub-agents help, and reports the state plus the ONE next step in German. Use when the user says "start", "neue Sitzung", "lies handoff", "wo waren wir" or invokes /start.
---

# Sitzung starten (Project-Friday / landstalker)

The user has no programming background, writes German, has only a Steam Deck: answer in German, plain words, short. Repo root `/home/deck/ProjectL`; paths below are relative to `landstalker/` unless they start with `remake/` or `.claude/`.
Counterpart at the end of a session: `/sitzung-beenden`.

## 1. Read (in this order, do NOT read huge files whole)
1. `CLAUDE.md` (already in context) and the memory index (`MEMORY.md`, already in context).
2. `docs/HANDOFF.md` is ~300 KB: never read it whole. Read:
   - lines 1-11 (read order, idea files, summary),
   - the NEWEST `## 0aNNN` entry: `grep -n '^## 0a' docs/HANDOFF.md | sort -t a -k2 -n | tail -3` (numbers are not in file order; the highest number is the latest), then `sed -n '/^## 0aNNN\./p'`,
   - section `## 2. NEXT STEPS`: only the first 2-3 entries (lowest negative number = newest),
   - section `## 3. How the user works` + `3a` (Deck rules) once per session (`grep -n '^## [0-9]' docs/HANDOFF.md` for line numbers; cut long lines with `cut -c1-800`).
3. `docs/LESSONS.md`: sections 1-3 and the LAST ~15 entries of section 9 (fragile spots, newest at the end).
4. `docs/INDEX.md`: the Status block (section 1) only; the rest on demand (bug catalog, tool cheat sheet, debug playbook).
5. Only when the topic needs it: `docs/DEBUGGING_INDEX.md` -> the matching part of `DEBUGGING.md`; idea files (`HUD_IDEAS.md`, `SPRINT_IDEAS.md`, `BOSS_RUSH_IDEAS.md`, `RENDERER_IDEAS.md`, `TIMING_PLAN.md`); for the remake `remake/README.md` + `remake/ASSETS.md`.
6. Names / ids: `python3 tools/sym.py <addr|text>`, `docs/ROOMS.md` / `ENTITIES.md` / `ITEMS.md` / `FLAGS.md`. Never read `symbols.json` whole.

## 2. Check the state
- `git status --short`, `git branch --show-current`, `git log --oneline -5`. Must be on `dev` (switch if not; never work on `main`). Untracked user files (videos, pictures) are not ours: do not commit or delete them.
- `git fetch origin dev && git status -sb` (behind? then `git pull origin dev`).
- Leftover agent worktrees: `ls .claude/worktrees 2>/dev/null`. They branch from `main`, not `dev` (LESSONS 9): only cherry-pick their commits onto dev after checking the diff; ask the user before removing them.
- On the Deck (ROM `/home/deck/Documents/NonSteamGames/landstalker/landstalker.md` exists): build state `ls -la landstalker/build/ 2>/dev/null | head`; new interpreter log `ls -la ~/interp.txt 2>/dev/null`; new user recordings `ls -t ~/aufnahmen | head -3`.

## 3. Model and Sonnet sub-agents (user wish 2026-10-30)
The lead (this session) plans, writes the delicate code, decides and talks to the user. Use **Sonnet sub-agents** (`Agent` tool, `model: "sonnet"`) where they save tokens without risk:
- **Good for agents:** doc propagation after a finding (INDEX status, HANDOFF entry, LESSONS 9, DEBUGGING section, FORMATS rows), symbol / unknowns bookkeeping, `check_docs.py` error fixing, long headless runs + log reading (bench, timebench, replays, lagstat measurements) with a short summary back, broad searches over the docs / generated C (`Explore`), re-baselining, mock-ups / previews to look at.
- **Not for agents:** patch code in `tools/patch_*.py` and the runtime (timing, renderer, options), anything "Off = bit exact" must protect, decisions for the user, merges / releases / tags, `~/Landstalker.sh` changes.
- Give every agent: the exact task, the files, the rules (no ROM-derived files in git, symbols with names, work on `dev`), and what to report back (short). Run independent agents in parallel in the background. If an agent uses `isolation: "worktree"`, tell it the base is `main` and it must start from `origin/dev` (`git checkout -B work origin/dev`).
- The lead CHECKS every agent result (diff / numbers) before it is committed or told to the user.
- Do not switch the session model yourself; if asked which model runs, use `get_session`.

## 4. Report to the user (German, short)
- Where we are (2-4 lines: last session, what is verified headless vs. confirmed by the user on the Deck).
- Open questions for the user from the last handoff (e.g. a yes / no decision) - ask them directly.
- The ONE next step you propose (+ at most 2 alternatives), and which parts you would give to Sonnet agents.
- Then wait for the user's choice before larger work. Commands for the user: one copyable block per step, absolute paths, progress output (`echo`), `|| exit` after `cd`.
