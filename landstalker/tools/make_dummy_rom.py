#!/usr/bin/env python3
"""Writes a tiny, copyright-free Mega Drive test ROM with battery RAM (header 'RA', like Landstalker) for the CI smoke test (no game code in it).
usage: make_dummy_rom.py out.md"""
import struct, sys
rom = bytearray(0x20000)
rom[0:8] = struct.pack(">II", 0x00FFFE00, 0x00000200)          # initial SP, initial PC
hdr = b"SEGA MEGA DRIVE ".ljust(0x10) + b"(C)TEST 2026.OCT".ljust(0x10) + b"PROJECT FRIDAY SMOKE TEST".ljust(0x30) + b"PROJECT FRIDAY SMOKE TEST".ljust(0x30)
hdr += b"GM 00000000-00".ljust(0x0E) + struct.pack(">H", 0)       # product, checksum
hdr += b"J".ljust(0x10)                                           # I/O support
hdr += struct.pack(">IIII", 0, len(rom) - 1, 0xFF0000, 0xFFFFFF)  # ROM start / end, RAM start / end
hdr += b"RA" + bytes([0xF8, 0x20]) + struct.pack(">II", 0x200001, 0x203FFF)   # battery RAM, odd bytes (as the real cartridge)
rom[0x100:0x100 + len(hdr)] = hdr
rom[0x200:0x204] = bytes.fromhex("60FE4E71")                       # bra.s *
open(sys.argv[1], "wb").write(rom)
print("dummy ROM written:", sys.argv[1], len(rom), "bytes")
