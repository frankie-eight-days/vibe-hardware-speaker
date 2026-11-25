# gates.sh board tag : release gates 1-5 on a board (scratch or closed live copy)
B=$1; T=$2
echo "== G1 DRC"; source drc.sh $B g_$T.json
echo "== G2 pads"; kp padcheck.py $B g_$T.json
echo "== G3 via nets"; kp vchk.py $B spec_fix.json $(ls spec_short.json spec_bus.json spec_res.json spec_isl.json spec_stf.json spec_land.json spec_fr.json 2>/dev/null) | head -2
echo "== G4 ref planes"; kp refcheck6.py $B ref_$T.json
echo "== G5 copper"; kp $LS/copper_balance.py $B
