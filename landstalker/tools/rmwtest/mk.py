import struct, json, sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
W = lambda *ws: b''.join(struct.pack('>H', w & 0xFFFF) for w in ws)
L = lambda v: struct.pack('>I', v)

prog = b''
def add(*words): 
    global prog; prog += W(*words)
def addl(v): 
    global prog; prog += L(v)

# --- setup ---
add(0x2049)                      # movea.l a1,a0 ... (placeholder, replaced below)
prog = b''
add(0x204F)                      # movea.l a7,a0      (save SP)
for n, base in ((1,0xFF3000),(2,0xFF3200),(3,0xFF3400),(4,0xFF3600),(5,0xFF3800),(6,0xFF3A00)):
    add(0x41F9 | (n << 9)); addl(base)         # lea (base).l,an
add(0x2E7C); addl(0xFF3C00)                   # movea.l #$FF3C00,a7
add(0x203C); addl(0x12345678)                 # move.l #$12345678,d0
add(0x223C); addl(0x0F0F0F0F)                 # move.l #$0F0F0F0F,d1
# seed memory around each pointer so the operations have real data to chew on
for n in (1,2,3,4,5,6):
    add(0x2080 | (n << 9))                      # move.l d0,(an)
    add(0x2141 | (n << 9), 4)                   # move.l d1,4(an)
    add(0x2140 | (n << 9), 0xFFFC)              # move.l d0,-4(an)
    add(0x2141 | (n << 9), 0xFFF8)              # move.l d1,-8(an)
add(0x2E80 | 0)                                 # move.l d0,(a7)
add(0x2F41, 4); add(0x2F40, 0xFFFC); add(0x2F41, 0xFFF8)   # (a7) neighbours
tests = [
 (0x8159,),            # or.w d0,(a1)+
 (0xC359,),            # and.w d1,(a1)+
 (0xD162,),            # add.w d0,-(a2)
 (0x931B,),            # sub.b d1,(a3)+
 (0xB11C,),            # eor.b d0,(a4)+
 (0xB11C,),            # eor.b d0,(a4)+  (keep a4 even)
 (0x525D,),            # addq.w #1,(a5)+
 (0x5326,),            # subq.b #1,-(a6)
 (0x4462,),            # neg.w -(a2)
 (0x461B,),            # not.b (a3)+
 (0xE3DC,),            # lsl.w (a4)+
 (0x01DD,),            # bset d0,(a5)+
 (0x01DD,),            # bset d0,(a5)+  (keep a5 even)
 (0x50DE,),            # st (a6)+
 (0x0059, 0x00F0),     # ori.w #$00F0,(a1)+
 (0x0222, 0x000F),     # andi.b #$0F,-(a2)
 (0x069B, 0x0000, 0x0001),  # addi.l #1,(a3)+
 (0x449D,),            # neg.l (a5)+
 (0x81A6,),            # or.l d0,-(a6)
 (0x4259,),            # clr.w (a1)+
 (0x32C0,),            # move.w d0,(a1)+
 (0x4A59,),            # tst.w (a1)+
 (0xD059,),            # add.w (a1)+,d0
 (0x811F,),            # or.b d0,(a7)+
 (0x5327,),            # subq.b #1,-(a7)
 (0x8159,),(0x8159,),  # or.w d0,(a1)+ twice more
]
for t in tests: add(*t)
# --- save results: a1..a7 and d0 into RAM at $FFF000 ---
for i, n in enumerate((1,2,3,4,5,6,7)):
    add(0x23C8 | n); addl(0xFFF000 + 4*i)      # move.l an,($FFF000+4i).l
add(0x23C0); addl(0xFFF040)                    # move.l d0,($FFF040).l
add(0x2E48)                                    # movea.l a0,a7   (restore SP)

def build(path, tail):
    rom = bytearray(0x10000)
    rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
    for v in range(2, 64): rom[v*4:v*4+4] = struct.pack('>I', 0x300)
    rom[0x300:0x302] = struct.pack('>H', 0x60FE)   # every other vector: bra.s *
    rom[0x100:0x110] = b'SEGA MEGA DRIVE '
    code = prog + tail
    rom[0x200:0x200+len(code)] = code
    open(path, 'wb').write(rom)
    return 0x200 + len(code)
end_ref = build('ref.bin', W(0x60FE))       # bra.s *
end_rec = build('rec.bin', W(0x4E75))       # rts
json.dump({'title':'t','seeds':{'0x000200':'sub_000200'},'offset_tables':[],'code_ranges':[['0x200', hex(end_rec)]]}, open('r.json','w'))

# eyeball: disassemble the test instructions
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
code = bytes(open('rec.bin','rb').read()[0x200:end_rec])
for i in md.disasm(code, 0x200):
    print(f'{i.address:04X}  {i.mnemonic:8s} {i.op_str}')
