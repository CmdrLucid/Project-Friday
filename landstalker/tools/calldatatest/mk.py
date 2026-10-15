#!/usr/bin/env python3
"""Inline-data-after-call test (reference core vs recompiled), see tools/patch_calldata.py.
helper skip2 ($300), skip6 ($320), pick ($340), terminal ($360), sub ($400); r.json carries call_data.
Expected RAM: FF0000=AA FF0001=BB FF0002=CC FF0003=DD, FF0010=1234 FF0012=0001 FF0014=0003."""
import json, struct
W = lambda *ws: b''.join(struct.pack('>H', w & 0xFFFF) for w in ws)
def bsr(at, to): return W(0x6100, (to - (at + 2)) & 0xFFFF)
code = bytearray(0x1000)
def put(a, b): code[a:a+len(b)] = b
# main at $200
m = 0x200; main = b''
main += bsr(m, 0x300);                    # bsr skip2
main += W(0x1234)                         # inline data
main += W(0x13FC, 0x00AA, 0x00FF, 0x0000) # move.b #$AA,$FF0000
a = m + len(main); main += bsr(a, 0x320)  # bsr skip6
main += W(0x0001, 0x0002, 0x0003)
main += W(0x13FC, 0x00BB, 0x00FF, 0x0001)
a = m + len(main); main += bsr(a, 0x340)  # bsr pick
main += W(0x0005, 0x0009, 0x0007, 0x0008, 0xFFFF)   # 2 pairs + terminator
main += W(0x13FC, 0x00CC, 0x00FF, 0x0002)
a = m + len(main); main += bsr(a, 0x400)  # bsr sub (calls the terminal helper)
main += W(0x13FC, 0x00DD, 0x00FF, 0x0003)
put(m, main); end = m + len(main)
put(0x300, W(0x2057, 0x3018, 0x33C0, 0x00FF, 0x0010, 0x2E88, 0x4E75))                    # skip2
put(0x320, W(0x2057, 0x3010, 0x33C0, 0x00FF, 0x0012, 0x3028, 0x0004, 0x33C0, 0x00FF, 0x0014, 0x5C97, 0x4E75))  # skip6
put(0x340, W(0x2057, 0x3018, 0x6B04, 0x5488, 0x60F8, 0x2E88, 0x4E75))                    # pick
put(0x360, W(0x588F, 0x4E75))                                                           # terminal: addq.l #4,sp / rts
s = bsr(0x400, 0x360) + W(0xFFFF, 0x1111, 0x2222)                                        # sub: bsr terminal + junk data
put(0x400, s)
def build(path, tail):
    rom = bytearray(0x10000)
    rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
    for v in range(2, 64): rom[v*4:v*4+4] = struct.pack('>I', 0x500)
    rom[0x500:0x502] = W(0x60FE)
    rom[0x100:0x110] = b'SEGA MEGA DRIVE '
    rom[0x200:0x1000] = code[0x200:0x1000]
    rom[end:end+len(tail)] = tail
    open(path, 'wb').write(rom)
build('ref.bin', W(0x60FE)); build('rec.bin', W(0x4E75))
json.dump({'title': 't', 'offset_tables': [],
           'seeds': {'0x000200': 't_main', '0x000300': 'h_skip2', '0x000320': 'h_skip6', '0x000340': 'h_pick',
                     '0x000360': 'h_term', '0x000400': 't_sub'},
           'call_data': {'0x000300': {'skip': 2}, '0x000320': {'skip': 6}, '0x000340': {'pick': True}, '0x000360': {'terminal': True}},
           'code_ranges': [['0x200', '0x420']]}, open('r.json', 'w'))
print("wrote ref.bin rec.bin r.json")
