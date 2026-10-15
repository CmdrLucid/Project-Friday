# Inline data after a call (reference core vs recompiled)

`python3 mk.py` writes ref.bin/rec.bin/r.json (copy `h.c` from tools/rmwtest; build like there).
Helpers read parameters at the return address and return past them (skip 2, skip 6, variable list)
or never return (terminal). Result with patch_calldata.py: RAM identical to the real core
(`aa bb cc dd`, params 1234/0001/0003); without `call_data` in r.json: garbage, nothing written.
