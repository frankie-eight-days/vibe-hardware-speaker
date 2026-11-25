export SP=$(cd "$(dirname "${(%):-%x}")" && pwd)   # was scratchpad/r6
export KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
export PRJ=/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test
export HWM=$PRJ/hw/mainboard
export LS=$HWM/layout_src
kp(){ $KPY "$@" 2>&1 | grep -v -e assert -e Debug -e "memory leak" -e "^$" ; true; }
