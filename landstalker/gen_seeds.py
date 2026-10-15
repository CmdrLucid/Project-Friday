#!/usr/bin/env python3
"""Write recomp.json seeds for Landstalker's computed-jump tables (US ROM).

Each entry is (first address, entry size in bytes, entry count). Addresses and
counts come from lordmir/landstalker_disasm (the jmp X(pc,dN) tables).
Add a row here when the log reports `no function at $XXXXXX`.
"""
import json, sys

TABLES = [
    (0x004AD8, 2, 16,  "DecompressLZ77Gfx copy slots (Duff's device)"),
    (0x00604C, 4, 47,  "ProcessFloorType bra.w table"),
    (0x0237DC, 4, 19,  "string effect bra.w table"),
    (0x009702, 2, 7,   "door size bra.s table"),
    (0x017918, 4, 104, "sprite behaviour bra.w table"),
    # computed-jump tables of bra.w entries (build.sh's expand_seeds.py grows these from one seed)
    (0x001936, 4, 32,  "HandleDirectionalControl (d-pad) table"),
    (0x0120FC, 4, 347, "CustomScriptActionTable (dialogue actions)"),
    (0x010D08, 4, 145, "TriggerActionJumpTable"),
    # jmp thunks the game copies into RAM (JumpInstr2) and calls: only the copy is seen
    (0x00427C, 2, 1,   "target of loc_409E thunk (sprite tile source setup)"),
    (0x00433E, 2, 1,   "target of loc_403C thunk"),
    # functions only reached by bne/beq tail branches or bsr.s from inside another routine: the generator does not split there
    (0x00673E, 2, 1,   "UpdateSwordCharge (ProcessActionButton tail branches): box lifting, sword charge"),
    (0x002458, 2, 1,   "sub_2458 (scroll update called from the tile loaders)"),
    # code the interpreter fallback ran (LANDSTALKER_INTERP_LOG), seeded so it is compiled natively
    # NOT seeded: $017CC0 is the middle of "btst.b #6,$48(a5)" at $017CBE (the interpreter logged it because generated code fell through to it)
    (0x0260DC, 2, 1,   "interp log win11"),
    (0x028F08, 2, 1,   "interp log win19 (dialogue/text code next to $028F6E/$028F9E/$028FD8; NPC without textbox)"),
    (0x017C68, 2, 1,   "interp log win18 (dialogue action helper, church save)"),
    (0x026112, 2, 1,   "interp log win14 (villager script, after $0260EE)"),
    (0x0260D0, 2, 1,   "interp log win13 (villager script area $0260BA..$0260EE)"),
    (0x0260EE, 2, 1,   "interp log win12 (next to $0260DC, villager script)"),
    (0x017B48, 2, 1,   "interp log win10 (script area near dialogue runner)"),
    (0x025F98, 2, 1,   "interp log win10 (villager/dialogue script)"),
    (0x025FB2, 2, 1,   "interp log win10 (villager/dialogue script)"),
    (0x003890, 2, 1,   "sub_3890: Friday animation DMA helper, reached by fall-through from sub_388C (interp log win9)"),
    (0x1A85C6, 2, 1,   "EnemyAI jump table start (bra.w entries EnemyAI_Bubble1_A ...; interp log dev1; expand_seeds expands the whole table, descent reaches the enemy AI code at $1A8000+)"),
    # item tables with 6-byte entries (bra.w + 2 data bytes); the code at $0085FC searches them and `jmp (a0)` into the matching entry
    (0x00F8C6, 2, 1,   "FadePaletteDownStep loop entry: TreeWarpFx ($00E48E) calls it with d7=$37 / a0=$FF0080 (jsr into the middle, after the moveq #$F,d7); interp log 2026-10-13 tree warp"),
    (0x0085F2, 2, 1,   "UseItemDispatch: called by bsr.w from $007756; stores the item id, searches the table, jmp (a0) / error sound (the analyzer started a bogus function at $0085F0)"),
    (0x008620, 6, 23,  "UseItemTable entries (bra.w ItemUse* + id word): $8620 .. $86A4 (ItemUseKey = $8698); 0xFFFF terminator at $86AA; interp log dev3"),
    (0x0086B0, 6, 6,   "PostUseItemTable entries (bra.w + id word): $86B0 .. $86CE (PostUseKey = $86C8); interp log dev2: key door"),
    (0x027732, 2, 1,   "XS_00FE: Statue of Jypta cutscene (trap #1 text, ScriptSleep, rts); ScriptJump target of cutscene ID 0xFE"),
    # HandleControlChars ($023150): text control codes, `jmp HandleControlChars(pc,d0.w)`, 4-byte bra.w entries with zero gaps
    (0x023150, 4, 16,  "HandleControlChars entries 0-15 (yes/no, newline, item name, waits, numeric variable ...)"),
    (0x0231A4, 4, 1,   "HandleControlChars entry 21"),
    (0x0231B4, 4, 5,   "HandleControlChars entries 25-28"),
]

seeds = {}
for start, size, count, _ in TABLES:
    for k in range(count):
        a = start + k * size
        seeds[f"0x{a:06X}"] = f"sub_{a:06X}"

# Routines that read inline data after the call and return past it (or never return): tools/patch_calldata.py.
# Addresses derived from lordmir/landstalker_disasm local-label arithmetic; "op"/"mask" = expected first words
# (checked by the generator, a mismatch ignores the entry). ScriptSleep is located from its call site.
CALL_DATA = {'ScriptSleep': {'site': '0x024B0E', 'skip': 2, 'op': '48E7', 'mask': '8080'}, '0x025D96': {'skip': 6, 'op': '48E7', 'mask': '8080'}, '0x025DBE': {'skip': 6, 'op': '48E7', 'mask': '8080'}, '0x025DEA': {'skip': 6, 'op': '48E7', 'mask': '8080'}, '0x025F60': {'skip': 4, 'op': '48E7', 'mask': 'FFFE'}, '0x0253CA': {'pick': True, 'op': '48E7', 'mask': '8040'}, '0x0252B0': {'terminal': True, 'op': '48E7', 'mask': '80E0'}, '0x024EF0': {'terminal': True, 'op': '48E7', 'mask': 'C080'}, '0x024F0A': {'terminal': True, 'op': '48E7', 'mask': 'E080'}}

out = sys.argv[1] if len(sys.argv) > 1 else "recomp.json"
json.dump({"title": "Landstalker", "seeds": dict(sorted(seeds.items())),
           "offset_tables": [],
           "trap_data": {"0": 1, "1": 1, "2": 1}, "call_data": CALL_DATA,
           # the analyzer's heuristic scans (jump-table / address-load / prologue guesses) only look here; tools/code_extent.py shows that
           # certain code lives below $030000 plus islands at $03xxxx (screens), $09A000, $11E000 and $1A0000-$1B0000 (enemy AI), see DEBUGGING; descent still follows jsr/jmp anywhere. Without this every run of 3 ROM-range longs in the
           # DATA areas became a bogus function (jt_XXXXXX), some inside real instructions (check_splits).
           "code_ranges": [["0x200", "0x30000"], ["0x30000", "0x40000"], ["0x9A000", "0xA2000"], ["0x11E000", "0x120000"], ["0x1A0000", "0x1B0000"]]}, open(out, "w"), indent=2)
print(f"wrote {len(seeds)} seeds to {out}")
