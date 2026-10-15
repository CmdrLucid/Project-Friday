# inputfuzz.py SEED OUT  -- random pad input after the massan.txt prefix (frames < 972, outside in Massan); run headless: GENRECOMP_INPUTSCRIPT=OUT LANDSTALKER_WIDE=48 build/landstalker --headless --frames 9100 ROM and grep for "RTS to" / "no function" / "interp:" (found the WIDE=48 queue overflow, 2026-10-10)
import random,sys
seed=int(sys.argv[1]); random.seed(seed)
lines=[l for l in open("/home/deck/massan.txt") if int(l.split()[0])<972]
f=1000; out=open(sys.argv[2],"w"); out.writelines(lines)
masks=[1,2,4,8,5,6,9,10,0,0x40,0x41,0x42,0x44,0x48,0x10,0x20]
while f<9000:
    out.write(f"{f} {random.choice(masks):04X}\n"); f+=random.randint(8,45)
