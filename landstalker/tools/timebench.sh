#!/bin/bash
# Timing bench (docs/TIMING_PLAN.md T0): thin wrapper, see tools/timebench.py for the options (--baseline / --compare / --verify-off / --counts)
exec python3 "$(dirname "$(readlink -f "$0")")/timebench.py" "$@"
