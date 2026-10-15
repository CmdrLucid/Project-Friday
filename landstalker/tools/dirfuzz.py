# dirfuzz.py SEED OUT -- random DIRECTION-only pad input (biased to LEFT) after the massan.txt prefix; finds room changes (village 592 <-> 424) for margin / transition tests; run headless and read room id $FF1204 from --ram-dump
import random,sys
seed=int(sys.argv[1]); random.seed(seed)
lines=[l for l in open("/home/deck/massan.txt") if int(l.split()[0])<972]
f=1000; out=open(sys.argv[2],"w"); out.writelines(lines)
while f<7000:
    m=random.choice([4,4,4,5,6,1,2,8,10,9])  # biased to LEFT-ish moves
    out.write(f"{f} {m:04X}\n"); f+=random.randint(30,90)
