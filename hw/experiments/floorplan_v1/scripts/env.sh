# Portable environment for the floor-plan scripts (was scratchpad/r6/env.sh).
export PRJ=${PRJ:-$(cd "$(dirname "${(%):-%x}")/../../../.." && pwd)}
export KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
export HWM=$PRJ/hw/mainboard
export LS=$HWM/layout_src
kp(){ $KPY "$@" 2>&1 | grep -v -e assert -e Debug -e "memory leak" -e "^$" ; true; }
