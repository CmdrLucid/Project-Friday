#!/usr/bin/env python3
"""stringdump.py ROM [out.json]: decodes ALL dialogue / message strings of a Landstalker ROM (US / Europe layout) to plain text.  Local use only: the output is derived from
the ROM (never commit it).  Format (FORMATS 'Text, strings'):
 * string id (word) = bank << 8 | index; banks = long pointers at StringBankPtrs $038368 (9 banks), each bank = entries one after the other, byte 0 of an entry = its LENGTH
   including this byte (GetComprStringPtr $02301C walks them), then a Huffman bit stream, MSB first.
 * every character is decoded with a tree selected by the PREVIOUS character (start: CHR_STR_BEGIN = $55): HuffTableOffsets $023D60 (word per previous char) -> tree in
   HuffTables $023E38: tree bits serialized, the leaf bytes stand BEFORE the tree in reverse order (port of DecodeChar $0246B2).
 * code $55 = string end, $00..$54 = font characters (charset_en: Main), $56.. = control characters (index = code - $56, see CONTROL).
Control code names: code $56 + k -> handler via ControlChars (disassembly stringfuncs1.asm) -> HandleControlChars order (FORMATS section 5); unknown ones are printed as {Cnn}."""
import json, struct, sys

HUFF_OFFS, HUFF_TREES, BANK_PTRS, N_BANKS = 0x23D60, 0x23E38, 0x38368, 9
STR_BEGIN, SEL_POINT = 0x55, 0x56
MAIN = (" 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz*.,?!/<>:-'\"%#&()=" + "↖↗↘↙")
# code - $56 -> handler (table ControlChars $023E??: word = ~handler index into HandleControlChars $023150): names by what the handler does
CONTROL = {0: "Ctl0", 1: "SoftNewLine", 2: "NewLine", 3: "Pause1s", 4: "Number", 5: "Speaker", 6: "Ctl6", 7: "Ctl7", 8: "WaitInput", 9: "Item", 10: "PopName",
           11: "CopyStr11", 12: "ContinuePrompt", 13: "NewLinePrompt", 14: "Pause1sOrInput", 15: "Pause1_5sOrInput", 16: "Pause2sOrInput", 17: "CopyStr17", 18: "Ctl18"}
# (Ctl0 = handler 21 `loc_230D6`, the first code of the Yes / No / Use / Equip strings 0000..0003; the YesNo prompt routine itself `$024748` is called by code, not by a string code)


class Bits:
    def __init__(self, data, pos):
        self.d, self.p, self.n, self.cur = data, pos, 0, 0
    def bit(self):
        if self.n == 0:
            self.cur, self.n, self.p = self.d[self.p], 8, self.p + 1
        self.n -= 1
        return (self.cur >> self.n) & 1


def decode_string(rom, start):
    """-> (text, end_address_of_entry) for the entry at start"""
    length = rom[start]
    sb = Bits(rom, start + 1)
    prev, out = STR_BEGIN, []
    for _ in range(4000):
        off = struct.unpack(">H", rom[HUFF_OFFS + 2 * prev:HUFF_OFFS + 2 * prev + 2])[0]
        a2 = HUFF_TREES + off
        tb = Bits(rom, a2)
        d5 = 0
        while True:                                  # port of DecodeChar loc_246DE / loc_246F8
            if tb.bit():                             # leaf
                ch = rom[a2 - 1 + d5]
                break
            if sb.bit() == 0:
                continue
            d4 = 0
            while True:
                if tb.bit():
                    d5 -= 1
                    d4 -= 1
                    if d4 == -1:
                        break
                else:
                    d4 += 1
        if ch == STR_BEGIN:
            break
        out.append(ch)
        prev = ch
    text = ""
    for ch in out:
        if ch < len(MAIN):
            text += MAIN[ch]
        elif ch >= SEL_POINT:
            k = ch - SEL_POINT
            text += "{%s}" % CONTROL.get(k, "C%02d" % k)
        else:
            text += "{?%02X}" % ch
    return text, start + length


# Uncompressed name / menu tables (LoadUncompressedString $02949A, sub_294B6): entry = count byte (NOT including itself) + that many font codes.
# Codes $69 hyphenation point, $6A breaking space (shown as a space or a line break in two-line names), $6B break point.
NAME_TABLES = (("char", 0x29552, 61), ("special", 0x296E0, 15), ("default", 0x29730, 1), ("item", 0x29732, 64), ("menu", 0x29A0A, 29))
NAME_CODES = {0x69: "{Hyphen}", 0x6A: "{BreakSpace}", 0x6B: "{BreakPoint}"}


def decode_names(rom):
    res = {}
    for name, start, count in NAME_TABLES:
        p = start
        for i in range(count):
            n = rom[p]
            res["%s:%02d" % (name, i)] = "".join(MAIN[c] if c < len(MAIN) else NAME_CODES.get(c, "{?%02X}" % c) for c in rom[p + 1:p + 1 + n])
            p += 1 + n
    return res


def main():
    rom = open(sys.argv[1], "rb").read()
    banks = [struct.unpack(">I", rom[BANK_PTRS + 4 * i:BANK_PTRS + 4 * i + 4])[0] for i in range(N_BANKS)]
    ends = banks[1:] + [None]
    res = {}
    for b, start in enumerate(banks):
        pos, idx = start, 0
        while idx < 256 and (ends[b] is None or pos < ends[b]):
            if rom[pos] == 0:
                break
            try:
                t, nxt = decode_string(rom, pos)
            except Exception as e:                  # stop at the first undecodable entry (end of the last bank)
                print("bank %d index %d @%06X: %s" % (b, idx, pos, e)); break
            res["%04X" % (b << 8 | idx)] = t
            pos, idx = nxt, idx + 1
        print("bank %d @%06X: %d strings" % (b, start, idx))
    names = decode_names(rom)
    print("names:", len(names), "entries (char, special, default, item, menu)")
    res.update(names)
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=0, ensure_ascii=False)
    else:
        for k in list(res)[:25]:
            print(k, repr(res[k]))
    print("total", len(res), "strings + names")

if __name__ == "__main__":
    main()
