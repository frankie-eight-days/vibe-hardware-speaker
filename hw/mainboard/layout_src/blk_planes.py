from blk_common import *
T=[];V=[];Z=[];J=[]; t,v,z,j=mk(T,V,Z,J,NET)
# board-wide pours. Outline inset 0.5 mm; antenna keep-out: nothing at X<63.3, nothing at X<75.3 outside Y 86..115 (LAYOUT_RULES 6)
G=[(75.3,75.5),(142.6,75.5),(143.5,74.0),(156.5,74.0),(157.4,75.5),(239.5,75.5),(239.5,120.5),(75.3,120.5),(75.3,115.0),(63.3,115.0),(63.3,86.0),(75.3,86.0)]
z('GND','In1.Cu',G,pri=0,clr=0.25,conn='solid',name='L2_GND_SOLID')
z('GND','F.Cu',G,pri=0,clr=0.25,conn='solid',name='L1_GND_POUR')
z('GND','B.Cu',G,pri=0,clr=0.25,conn='solid',name='L4_GND_POUR')
z('GND','In2.Cu',G,pri=0,clr=0.3,conn='solid',name='L3_GND_FILL')
# L3 power partition
z('PVDD','In2.Cu',[(97.5,85.6),(202.5,85.6),(202.5,109.4),(176.6,109.4),(176.6,101.0),(118.0,101.0),(118.0,109.4),(97.5,109.4)],pri=1,clr=0.3,conn='solid',name='L3_PVDD')
z('VSYS','In2.Cu',[(118.4,101.4),(176.2,101.4),(176.2,110.6),(180.2,110.6),(180.2,120.5),(118.4,120.5)],pri=1,clr=0.3,conn='solid',name='L3_VSYS')
z('3V3','In2.Cu',[(63.3,86.0),(75.3,86.0),(75.3,75.5),(239.5,75.5),(239.5,85.2),(97.1,85.2),(97.1,109.8),(118.0,109.8),(118.0,120.5),(75.3,120.5),(75.3,115.0),(63.3,115.0)],pri=1,clr=0.3,conn='solid',name='L3_3V3')
# extra plane vias: bulk caps, charger SYS
for x,y in [(142.5,88.3),(146.7,88.3),(153.4,88.3),(142.5,86.2),(146.7,86.2),(150.0,87.3),(142.4,100.6),(146.8,100.6),(142.4,99.3),(146.8,99.3)]: v('PVDD',x,y)
for x,y in [(142.4,96.0),(146.8,96.0),(153.3,96.0),(157.6,96.0),(142.4,108.6),(146.8,108.6),(142.4,110.0),(146.8,110.0),(150.0,96.0)]: v('GND',x,y)
for x in (171.4,173.6,175.8,178.0,180.0): v('VSYS',x,107.0)
# buck VIN fed from the boost VIN pour on an L4 strip (buck draws < 0.6 A)
j('VSYS',(99.6,114.6),(124.4,118.0),layers=['B.Cu'],start='B.Cu',w=0.8,res=0.05,clr=0.2,name='BUCK_VIN_L4',win=(96,112,126,120.6),maxit=4000000)
