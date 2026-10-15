import struct, random, json, sys
# --- hand-assembled DecompressLZ77Gfx ($4AB2..$4B13), from landstalker_disasm gamelogic3.asm
W = lambda *ws: b''.join(struct.pack('>H', w) for w in ws)
code = W(0x780F,            # 4AB2 moveq #15,d4
         0x7607,            # 4AB4 moveq #7,d3
         0x1018,            # 4AB6 move.b (a0)+,d0
         0x6B4A,            # 4AB8 bmi.s loc_4B04
         0x4241,            # 4ABA clr.w d1
         0x1218,            # 4ABC move.b (a0)+,d1
         0x3401,            # 4ABE move.w d1,d2
         0xC204,            # 4AC0 and.b d4,d1
         0xD201,            # 4AC2 add.b d1,d1
         0xE94A,            # 4AC4 lsl.w #4,d2
         0x1418,            # 4AC6 move.b (a0)+,d2
         0x4A42,            # 4AC8 tst.w d2
         0x6746,            # 4ACA beq.s locret_4B12
         0x2649,            # 4ACC movea.l a1,a3
         0x96C2,            # 4ACE suba.w d2,a3
         0x12DB, 0x12DB,    # 4AD0,4AD2 move.b (a3)+,(a1)+ x2
         0x4EFB, 0x1002)    # 4AD4 jmp loc_4AD8(pc,d1.w)
code += W(*([0x12DB] * 16))  # 4AD8..4AF6
code += W(0xD000,            # 4AF8 add.b d0,d0
          0x5BCB, 0xFFBE,    # 4AFA dbmi d3,loc_4ABA
          0x5ACB, 0x0004,    # 4AFE dbpl d3,loc_4B04
          0x60B0,            # 4B02 bra.s loc_4AB4
          0x12D8,            # 4B04 move.b (a0)+,(a1)+
          0xD000,            # 4B06 add.b d0,d0
          0x5ACB, 0xFFFA,    # 4B08 dbpl d3,loc_4B04
          0x5BCB, 0xFFAC,    # 4B0C dbmi d3,loc_4ABA
          0x60A2,            # 4B10 bra.s loc_4AB4
          0x4E75)            # 4B12 rts
assert len(code) == 0x4B14 - 0x4AB2, hex(len(code))

# --- compressor matching the format the routine decodes
def compress(data):
    out = bytearray(); toks = []
    i = 0
    while i < len(data):
        best = (0, 0)
        for off in range(1, min(i, 4095) + 1):
            l = 0
            while l < 18 and i + l < len(data) and data[i + l - off] == data[i + l] if i + l - off >= 0 else False:
                l += 1
            if l > best[0]: best = (l, off)
        if best[0] >= 3:
            l, off = best
            n = 18 - l
            toks.append(('m', bytes([((off >> 4) & 0xF0) | n, off & 0xFF]))); i += l
        else:
            toks.append(('l', bytes([data[i]]))); i += 1
    toks.append(('m', bytes([0x00, 0x00])))   # offset 0 = end
    for k in range(0, len(toks), 8):
        grp = toks[k:k + 8]
        ctrl = 0
        for j, (t, _) in enumerate(grp):
            if t == 'l': ctrl |= 0x80 >> j
        out.append(ctrl)
        for _, b in grp: out += b
    return bytes(out)

random.seed(7)
orig = bytearray()
while len(orig) < 3000:
    r = random.random()
    if r < 0.4: orig += bytes(random.randrange(256) for _ in range(random.randrange(1, 12)))
    elif r < 0.7 and orig: 
        s = random.randrange(len(orig)); orig += orig[s:s + random.randrange(3, 40)]
    else: orig += bytes([random.randrange(4)]) * random.randrange(3, 30)
orig = bytes(orig)
comp = compress(orig)
rom = bytearray(0x20000)
rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
rom[0x100:0x110] = b'SEGA MEGA DRIVE '
rom[0x200:0x202] = W(0x4E75)
rom[0x4AB2:0x4AB2 + len(code)] = code
rom[0x10000:0x10000 + len(comp)] = comp
open('test.bin', 'wb').write(rom); open('orig.bin', 'wb').write(orig)
seeds = {f'0x{0x4AB2:06X}': 'sub_004AB2'}
for k in range(16): seeds[f'0x{0x4AD8 + 2 * k:06X}'] = f'sub_{0x4AD8 + 2 * k:06X}'
json.dump({'title': 'lz', 'seeds': seeds, 'offset_tables': [], 'code_ranges': [['0x4AB2', '0x4B14']]}, open('recomp.json', 'w'))
print('orig', len(orig), 'comp', len(comp))
