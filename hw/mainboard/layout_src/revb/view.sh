#!/bin/zsh
# view.sh board layers out.png x0 y0 x1 y1 [px_per_mm]
B=$1; LAYERS=$2; OUT=$3; S=${8:-10}; T=$(mktemp -d)
kicad-cli pcb export svg --mode-single --layers "$LAYERS" --page-size-mode 0 --exclude-drawing-sheet -o $T/a.svg $B >/dev/null 2>&1
python3 - "$4" "$5" "$6" "$7" "$S" $T <<'PY'
import re,sys
x0,y0,x1,y1,S=map(float,sys.argv[1:6]); T=sys.argv[6]
s=open(T+'/a.svg').read()
s=re.sub(r'viewBox="[^"]*"',f'viewBox="{x0} {y0} {x1-x0} {y1-y0}"',s,count=1)
s=re.sub(r'width="[^"]*"',f'width="{(x1-x0)*S}"',s,count=1); s=re.sub(r'height="[^"]*"',f'height="{(y1-y0)*S}"',s,count=1)
open(T+'/b.svg','w').write(s)
PY
rsvg-convert -b white $T/b.svg -o $OUT; rm -rf $T
