# Rev B geometry decisions (KiCad mm). Shared by prep.py / dsn.py / checks.
REAR=[(75.3,75.5),(239.5,75.5),(239.5,85.3),(75.3,85.3)]                 # L3 rear corridor strip (old +3V3 strip)
DIP=[(137.0,85.0),(176.0,85.0),(176.0,95.2),(137.0,95.2)]                 # corridor dip past USB-C/H4 (PVDD L3 starts at Y95.7 here)
LEFT=[(63.3,85.0),(97.4,85.0),(97.4,113.0),(95.3,113.0),(95.3,115.0),(63.3,115.0)]                  # MCU end (old +3V3 block, now GND fill + signals)
CORR=[REAR,DIP,LEFT]
# L3 GND overrides (pri 2) : old +3V3 L3 polygon, and the dip
L3_3V3_OLD=[(63.3,86.0),(75.3,86.0),(75.3,75.5),(239.5,75.5),(239.5,85.2),(97.1,85.2),(97.1,109.8),(118.0,109.8),(118.0,120.5),(75.3,120.5),(75.3,115.0),(63.3,115.0)]
L3_GND_OVR=[(63.3,86.0),(75.3,86.0),(75.3,75.5),(239.5,75.5),(239.5,85.2),(176.0,85.2),(176.0,95.2),(137.0,95.2),(137.0,85.2),(97.1,85.2),(97.1,109.8),(118.0,109.8),(118.0,120.5),(75.3,120.5),(75.3,115.0),(63.3,115.0)]
ZONES=[
 dict(net='GND',layer='In2.Cu',pts=L3_GND_OVR,priority=2,clearance=0.3,pad_connection='solid',name='L3_GND_REVB_CORR',min_width=0.2),
 # L4 PVDD spines (3 mm): along each amp's PVDD via column, joining both pin-row ends; left one runs on to the boost C_OUT PVDD vias/TP901
 dict(net='/amp_left/PVDD',layer='B.Cu',pts=[(110.4,84.4),(126.6,84.4),(126.6,91.9),(128.6,91.9),(130.9,94.2),(130.9,96.2),(129.0,96.2),(127.2,94.4),(125.0,94.4),(125.0,86.0),(113.4,86.0),(113.4,109.4),(110.4,109.4)],
      priority=2,clearance=0.25,pad_connection='solid',name='L4_PVDD_SPINE_L',min_width=0.25),
 dict(net='/amp_left/PVDD',layer='B.Cu',pts=[(176.4,85.6),(189.8,85.6),(189.8,109.4),(186.8,109.4),(186.8,88.6),(176.4,88.6)],
      priority=2,clearance=0.25,pad_connection='solid',name='L4_PVDD_SPINE_R',min_width=0.25),
]
# right spine -> L3 PVDD plane (X>176): via column at the spine's west end
VIAS_ADD=[dict(net='/amp_left/PVDD',x=x,y=y,size=0.6,drill=0.3) for x,y in ((177.2,87.0),(178.6,87.0),(180.0,87.0))]
# compensating PVDD vias: L1 C_OUT band (Y85.3-86.9) -> L3 PVDD, west of the dip (the 6 bulk-cap vias inside the dip go)
VIAS_ADD+=[dict(net='/amp_left/PVDD',x=x,y=86.15,size=0.6,drill=0.3) for x in (131.0,133.0,135.0)]
DEL_VIAS_AT=[(142.5,88.3),(146.7,88.3),(153.4,88.3),(142.5,86.2),(146.7,86.2),(150.0,87.3)]   # C920/C401 +pad vias to L3 PVDD (inside corridor dip)
# R904 (boost FB divider) rev A defects: L4 Kelvin/FB tracks ended under F.Cu pads with no via
FIX_DEL_TRACKS=[('/amp_left/PVDD','B.Cu',(131.525,96.9),(133.075,96.9)),('/rails/BST_FB','B.Cu',(134.2,96.9),(134.725,96.9))]
FIX_ADD_TRACKS=[dict(net='/amp_left/PVDD',layer='B.Cu',x1=131.525,y1=96.9,x2=132.3,y2=96.9,w=0.25),
                dict(net='/amp_left/PVDD',layer='F.Cu',x1=132.3,y1=96.9,x2=133.075,y2=96.9,w=0.3),
                dict(net='/rails/BST_FB',layer='B.Cu',x1=134.2,y1=96.9,x2=134.2,y2=96.05,w=0.2),
                dict(net='/rails/BST_FB',layer='F.Cu',x1=134.2,y1=96.05,x2=134.7,y2=96.55,w=0.2)]
FIX_ADD_VIAS=[dict(net='/amp_left/PVDD',x=132.3,y=96.9,size=0.5,drill=0.25),dict(net='/rails/BST_FB',x=134.2,y=96.05,size=0.5,drill=0.25)]
# charger BTST caps: SW-side via -> L3 SW link (rev A blk_swlinks jobs never completed)
JOBS=[dict(net='/charger/CHG_SW1',src=(161.3,111.3),dst=(166.25,111.85),layers=['In2.Cu'],w=0.4,clr=0.25,name='BTST1_SW1_L3'),
      dict(net='/charger/CHG_SW2',src=(173.25,113.3),dst=(167.75,113.25),layers=['In2.Cu'],w=0.4,clr=0.25,name='BTST2_SW2_L3')]
# buck VIN feed: L3 VSYS tongue from the VSYS plane (X118.4) to the BUCK_VIN vias (rev A fed it from nowhere once L3 front-left was +3V3)
# (rev A already feeds the buck VIN with an L4 VSYS track ending at the via (99.6,114.6); that via just never touched BUCK_VIN)
FIX_ADD_TRACKS+=[dict(net='/charger/VSYS',layer='F.Cu',x1=99.6,y1=114.6,x2=99.6,y2=115.3,w=0.6)]
DEL_VIAS_AT+=[(96.8,114.6),(98.2,114.6)]
# C301 (+) L3 vias had no L1 connection: 0.6 mm L1 stubs to the C301 pad 1
FIX_ADD_TRACKS+=[dict(net='/amp_left/PVDD',layer='F.Cu',x1=a,y1=y,x2=c,y2=y,w=0.6) for a,c in ((142.4,143.6),(146.8,145.6)) for y in (99.3,100.6)]
# rev A critical I2S_BCLK L4 run under U301 ended under the U301.7 pad (no via) and ran along the L3 PVDD/VSYS split: removed (BCLK re-routed)
FIX_DEL_TRACKS+=[('/I2S_BCLK','B.Cu',(117.3,109.875),(118.35,108.825)),('/I2S_BCLK','B.Cu',(118.35,108.825),(118.35,97.925)),('/I2S_BCLK','F.Cu',(117.3,110.175),(117.3,109.875))]
DEL_VIAS_AT+=[(117.3,109.875)]
# rev A connectivity defects in frozen stages: the switch-node pours never touched their IC pins (fill pulled back by clearance/min-width)
FIX_ADD_TRACKS+=[dict(net='/rails/BUCK_SW',layer='F.Cu',x1=104.74,y1=117.05,x2=105.9,y2=117.05,w=0.3),       # U951 pin 5 -> BUCK_SW pour
                 dict(net='/charger/CHG_SW2',layer='F.Cu',x1=167.45,y1=110.9,x2=167.45,y2=111.8,w=0.2)]      # U701 pin 26 -> CHG_SW2_IC pour
