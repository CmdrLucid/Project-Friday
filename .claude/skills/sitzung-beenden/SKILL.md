---
name: sitzung-beenden
description: Ends a ProjectL/Landstalker work session cleanly - runs the doc checks, records everything learned (symbols, unknowns, formats, status, handoff) and pushes to dev. Use when the user says "Sitzung beenden", "Doku-Check", "Feierabend", "wir sind fertig" or invokes /sitzung-beenden.
---

# Sitzung beenden (Project-Friday / landstalker)

The user has no programming background and writes German: answer in German, plain words, no jargon dumps. Work in `/…/ProjectL` (repo root); paths below are relative to `landstalker/`.
Never commit ROMs, generated C, dumps, saves or other ROM-derived files. Never touch `main` (only on explicit request: PR dev -> main).

## Steps (do them in order, report briefly at the end)
1. **Overview:** `git status --short` and `git log --oneline -10`. List what changed this session in 3-6 bullet points (for yourself; reuse for the status text).
2. **Learned addresses/names:** every address, function, RAM variable or table learned this session -> `docs/symbols.json` (addr `0xXXXXXX`, name, kind, note, confidence `verified` only with disassembly/call stack/log/test proof, else `inferred`). Names we invented: `inferred (name)`.
3. **Seen but not understood:** anything from logs/tests we did not understand -> `python3 tools/unknowns.py from-log LOG --ctx "where/what/build"` or `unknowns.py add ADDR --where ... --caller ... --note "pattern"`. Then `python3 tools/unknowns.py scan-docs && python3 tools/unknowns.py triage && python3 tools/unknowns.py sync`.
4. **Data layouts:** new/confirmed/corrected struct or table facts -> `docs/FORMATS.md` with status V (verified) / I (inferred) / ? (open) and date.
5. **Evidence log + bug catalog:** new findings, build checksums, test results -> `docs/DEBUGGING.md` (dated section) and, for bugs, the catalog in `docs/INDEX.md` section 3; then `python3 tools/make_doc_index.py`.
6. **Status:** update the Status block in `docs/INDEX.md`, and `docs/HANDOFF.md` sections 1 (Where we are: what was verified headless vs. what the user confirmed by playing) and 2 (next steps), fragile spots in `docs/LESSONS.md` section 9. New ideas/plans get a date and the dev commit they rest on (format of `docs/RENDERER_IDEAS.md`).
7. **Check:** `python3 tools/check_docs.py -v` must end with `errors: 0`. Fix every ERROR (add missing symbols), rerun.
8. **Commit and push:** `git add -A`, check `git status` once more (no ROM-derived files), commit with a clear message and the attribution footer required by the session, `git push origin <current-branch>:dev` (and the session branch if it differs). Retry network failures up to 4 times with 2/4/8/16 s backoff.
9. **Report to the user (German, short):** what was done, what is verified and by whom (headless vs. user played), what is still open, the ONE next step, and if a new ZIP/pull is needed the exact command or URL (`https://github.com/cmdrlucid/Project-Friday/archive/refs/heads/dev.zip`). Do not claim "verified on the Deck" for things only a human can judge (sound, look, feel).
