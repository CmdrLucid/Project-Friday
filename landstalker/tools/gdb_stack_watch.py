# gdb script: find the host code that zeroes a 68K RAM slot (hardware watchpoint on work_ram).
# usage (Deck):  gdb -q -batch -x tools/gdb_stack_watch.py --args build/landstalker ROM
# Plays the game normally; stops at the FIRST change away from EXPECT (it may be written in two 16-bit halves) and prints the host backtrace.
# OFF/EXPECT default to the sub_24A78 return slot: 68K $FFFFE8 holding $0001895E (host order: 0x895E0001).
import gdb

OFF = 0xFFE8
EXPECT = 0x895E0001


class Watch(gdb.Breakpoint):
    last = 0

    def stop(self):
        now = int(gdb.parse_and_eval("*(unsigned int *)((char *)&work_ram + %d)" % OFF)) & 0xFFFFFFFF
        old, Watch.last = Watch.last, now
        if old == EXPECT and now != EXPECT:
            gdb.write("\n=== work_ram+0x%X changed %08X -> %08X ===\n" % (OFF, old, now))
            gdb.execute("bt 25")
            gdb.execute("info registers rip")
            return True
        return False


gdb.execute("set debuginfod enabled off")
gdb.execute("set pagination off")
gdb.execute("break main")
gdb.execute("run")
Watch("*(unsigned int *)((char *)&work_ram + %d)" % OFF, gdb.BP_WATCHPOINT, gdb.WP_WRITE)
gdb.execute("continue")
