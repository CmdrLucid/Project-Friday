import struct, json
W=lambda *ws: b''.join(struct.pack('>H',w&0xFFFF) for w in ws)
L=lambda v: struct.pack('>I',v)
p=b''
def add(*w):
    global p; p+=W(*w)
def addl(v):
    global p; p+=L(v)
add(0x204F)                                   # movea.l a7,a0
add(0x2E7C); addl(0xFF3C00)                   # movea.l #$FF3C00,a7
add(0x203C); addl(0x8001FFF0)                 # d0
add(0x243C); addl(0x00007F80)                 # d2 (word has bit15 clear)
add(0x263C); addl(0xAAAA8123)                 # d3 (word negative)
add(0x283C); addl(0x11112222)                 # d4
add(0x2A3C); addl(0x33334444)                 # d5
add(0x2C3C); addl(0x5555FF01)                 # d6
add(0x2E3C); addl(0x77778002)                 # d7
add(0x48A7, 0xA300)                           # movem.w d0/d2/d6-d7,-(sp)?? mask predec; see below
add(0x4C9F, 0x00C5)                           # movem.w (sp)+,d0/d2/d6/d7 (loads sign-extended)
add(0x48A7, 0x0800)                           # movem.w d4,-(sp)
add(0x4C9F, 0x0010)                           # movem.w (sp)+,d4
add(0x48E7, 0x0404)                           # movem.l d5/a5,-(sp)  placeholder mask
add(0x4CDF, 0x2020)                           # movem.l (sp)+,d5/a5
# pc-relative indexed byte: move.b $4(pc,d0.w),d2 style; d0.w=2
add(0x7002)                                   # moveq #2,d0
add(0x143B, 0x0004)                           # move.b 4(pc,d0.w),d2 (ext word D0.w, disp 4)
add(0x6008)                                   # jmp 8(pc) -> skip table
add(0x0102, 0x0304, 0x0506, 0x0708)           # table
# adda.w negative / cmpa.l imm / lsl.b / sub.w mem
add(0x2C7C); addl(0xFF3100)                   # movea.l #$FF3100,a6
add(0x323C, 0xFFF8)                           # move.w #-8,d1
add(0xDCC1)                                   # adda.w d1,a6
add(0x3D3C, 0x1234)                           # move.w #$1234,-(a6)
add(0x7600); add(0x163C, 0x00F5)              # moveq #0,d3; move.b #$F5,d3
add(0xE90B)                                   # lsl.b #4,d3
add(0xB8C3)                                   # cmpa.w d3,a4
save=[(0xFF3000+4*i) for i in range(16)]
regs=[('d',0),('d',1),('d',2),('d',3),('d',4),('d',5),('d',6),('d',7),('a',5),('a',6)]
for i,(k,n) in enumerate(regs):
    mv = 0x23C0|(n if k=='d' else 8|n)
    add(mv); addl(0xFF3000+4*i)
add(0x2E48)
def build(path,tail):
    rom=bytearray(0x10000)
    rom[0:8]=struct.pack('>II',0x00FFFE00,0x200)
    for v in range(2,64): rom[v*4:v*4+4]=struct.pack('>I',0x300)
    rom[0x300:0x302]=W(0x60FE)
    rom[0x100:0x110]=b'SEGA MEGA DRIVE '
    c=p+tail; rom[0x200:0x200+len(c)]=c
    open(path,'wb').write(rom); return 0x200+len(c)
build('ref.bin',W(0x60FE)); e=build('rec.bin',W(0x4E75))
json.dump({'title':'t','seeds':{'0x000200':'sub_000200'},'offset_tables':[],'code_ranges':[['0x200',hex(e)]]},open('r.json','w'))
from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
for i in md.disasm(open('rec.bin','rb').read()[0x200:e],0x200): print(hex(i.address),i.mnemonic,i.op_str)
