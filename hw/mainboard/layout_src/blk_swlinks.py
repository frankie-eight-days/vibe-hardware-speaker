from blk_common import *
T=[];V=[];Z=[];J=[]; t,v,z,j=mk(T,V,Z,J,NET)
# BTST caps' SW-side vias -> the SW1/SW2 L3 links (EVM item 3: vias on one side of the BTST cap)
j('SW1',(161.3,111.3),(164.6,104.2),layers=['In2.Cu'],start='In2.Cu',w=0.4,res=0.05,clr=0.25,name='BTST1_SW1_L3',margin=2)
j('SW2',(173.25,113.3),(169.9,104.2),layers=['In2.Cu'],start='In2.Cu',w=0.4,res=0.05,clr=0.25,name='BTST2_SW2_L3',margin=2)
