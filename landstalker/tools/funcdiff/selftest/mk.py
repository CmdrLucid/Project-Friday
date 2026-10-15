#!/usr/bin/env python3
"""Self test for funcdiff: builds a tiny test ROM (rom.bin, ram.bin, rom.json) around the Landstalker collision routines ($31A0/$31A6/$31F8/$31FE, stubs
at $380/$386/$38C/$392) plus simple stand-ins for MultiplyD1By148 / MultiplyD2By148, a random height map and an entity.
The 150 bytes of game code of the collision routines are NOT stored in this repository: they are read from YOUR ROM at the addresses below.
usage: mk.py [path/to/your.rom]   (default: $LANDSTALKER_ROM or the Steam Deck path)"""
import json, os, random, struct, sys
ROMFILE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LANDSTALKER_ROM", "/home/deck/Documents/NonSteamGames/landstalker/landstalker.md")
if not os.path.isfile(ROMFILE):
    sys.exit("mk.py: ROM not found (" + ROMFILE + "): give the path of your Landstalker ROM as argument")
game = open(ROMFILE, "rb").read()
# (address, length) of the routines copied from the ROM (same addresses in the test ROM)
GAME_CODE = [(12704, 6), (12710, 4), (12714, 78), (12792, 6), (12798, 4), (12802, 74)]
code = {
 0x380: "4ef9000031a6", 0x386: "4ef9000031fe", 0x38C: "4ef9000031a0", 0x392: "4ef9000031f8",
 0xC3A0: "c2fc00944e75",   # mulu.w #148,d1 ; rts   (stand-in)
 0xC3AA: "c4fc00944e75",   # mulu.w #148,d2 ; rts   (stand-in)
}
rom = bytearray(0x10000)
rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
for v in range(2, 64): rom[v * 4:v * 4 + 4] = struct.pack('>I', 0x300)
rom[0x300:0x302] = struct.pack('>H', 0x60FE)
rom[0x100:0x110] = b'SEGA MEGA DRIVE '
for a, n in GAME_CODE:
    rom[a:a + n] = game[a:a + n]
for a, h in code.items():
    b = bytes.fromhex(h); rom[a:a + len(b)] = b
open('rom.bin', 'wb').write(rom)
rnd = random.Random(5)
ram = bytearray(65536)
def put(a, v): ram[a & 0xFFFF ^ 1] = v
# height map: 148 bytes per row, 74 words per row; rows indexed by y>>4, cells by x>>3 (even offsets)
for row in range(80):
    for cell in range(74):
        h = 0 if rnd.random() < 0.55 else rnd.randrange(1, 12)
        put(0xD192 + row * 148 + cell * 2, h | (rnd.choice([0, 0x80, 0x10]) if rnd.random() < 0.1 else 0))
        put(0xD192 + row * 148 + cell * 2 + 1, rnd.randrange(256))
open('ram.bin', 'wb').write(ram)
seeds = {'0x%06X' % a: 'f_%06X' % a for a in (0x31A0, 0x31A6, 0x31F8, 0x31FE, 0x380, 0x386, 0x38C, 0x392, 0xC3A0, 0xC3AA)}
json.dump({'title': 't', 'seeds': seeds, 'offset_tables': [], 'code_ranges': [['0x380', '0x398'], ['0x31A0', '0x324C'], ['0xC3A0', '0xC3B0']]}, open('rom.json', 'w'))
print('wrote rom.bin ram.bin rom.json')
