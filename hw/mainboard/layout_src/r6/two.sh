# two.sh board out.png x0 y0 x1 y1 layer1 layer2 ...
B=$1; O=$2; shift 2; X=($1 $2 $3 $4); shift 4; fs=()
for L in "$@"; do kp plotl.py $B $L /tmp/_p_$L.png ${X[@]} --fill; fs+=(/tmp/_p_$L.png); done
$KPY -c "
import sys;from PIL import Image;I=[Image.open(f) for f in sys.argv[2:]];c=Image.new('RGB',(sum(i.width for i in I),max(i.height for i in I)),'white');x=0
for i in I: c.paste(i,(x,0)); x+=i.width
c.save(sys.argv[1])" $O ${fs[@]}
