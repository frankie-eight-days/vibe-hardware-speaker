# Rev B 6-layer geometry decisions (KiCad mm). Used by plan_n1.py (native step 1), k1ops (Konnect), fix stage.
NETS={'PVDD':'/amp_left/PVDD','VSYS':'/charger/VSYS','DP':'/usb_power/USB_DP','DN':'/usb_power/USB_DN','FB':'/rails/BST_FB'}
# ---- native step 1: zone replace by UUID (outline only; same net/layer/priority) ----
ZONE_REPLACE={
 # CHG_SYS: take in the rotated C716 VSYS pad (C716 rot 180 at (167.80,107.95): GND pad over C707.2 / pin 27 -> SYS loop closes straight down)
 '65c67ae7':[(167.75,111.25),(167.75,110.05),(167.95,109.8),(167.95,108.65),(168.1,108.65),(168.1,107.45),(169.25,107.45),(169.25,106.3),(180.4,106.3),(180.4,107.65),(169.75,107.65),(169.75,109.7),(169.0,109.9),(168.15,111.25)],
 # BUCK_VIN: reach the three VSYS feed vias at y 114.6 (rev A pour stopped 0.2 mm short)
 'f47e4167':[(96.2,114.2),(102.2,114.2),(102.2,116.2),(103.0,116.25),(103.0,116.65),(102.1,116.65),(101.9,116.2),(96.2,116.2)],
 # In3 VSYS: take the charger SYS vias at X 176-180 (they sat in PVDD); PVDD gives up that corner
 'a98884f9':[(118.4,101.4),(176.2,101.4),(176.2,104.2),(181.0,104.2),(181.0,110.6),(180.2,110.6),(180.2,120.5),(118.4,120.5)],
 'a6ac5efa':[(97.5,85.6),(202.5,85.6),(202.5,109.4),(181.6,109.4),(181.6,103.6),(176.6,103.6),(176.6,101.0),(118.0,101.0),(118.0,109.4),(97.5,109.4)],
 # CHG_BAT neck at pins 22/23: wide part starts 0.45 mm earlier (SDRV via clearance-limited)
 '61b6ef26':[(168.95,110.98),(170.1,110.98),(170.1,110.2),(178.05,110.2),(178.05,114.6),(176.95,114.6),(176.95,111.75),(168.95,111.75)],
}
# ---- native step 1: deletions (resolved to UUIDs on the 4-layer original) ----
DEL_TRACK_PREFIX=['267d254e','6936174a','7d166798','8d52c741','b78ebd44','c8f19a4d','d131c43b','e7eff1cf',   # USB_DP 0.28 -> 0.11 reroute (U601 moved)
 '266df0dd','46bfa717','4d115e4c','6b8778e7','9299241e','99784123','9e148cfa','daf5da22','d2ef896f','cac92ee5',  # USB_DN + its B.Cu jumper/via
 '965638b8',                                                                                                       # U601 pin5 +3V3 stub (U601 moves)
 '326cbdcb']                                                                                                       # R904 Kelvin B.Cu end (ends under pad, no via)
DEL_TRACK_RULES=[('/rails/BST_FB','B.Cu',(134.2,96.9),(134.725,96.9)),
 ('/I2S_BCLK','B.Cu',(117.3,109.875),(118.35,108.825)),('/I2S_BCLK','B.Cu',(118.35,108.825),(118.35,97.925)),('/I2S_BCLK','F.Cu',(117.3,110.175),(117.3,109.875))]
DEL_VIAS_AT=[('+3V3',141.96,83.60),('/I2S_BCLK',117.3,109.875)]
DEL_DUP_VIAS=True     # stacked duplicate vias (same net, same position): keep one
# ---- Konnect step: zones / part moves ----
OUTLINE=[(75.3,75.5),(142.6,75.5),(143.5,74.0),(156.5,74.0),(157.4,75.5),(239.5,75.5),(239.5,120.5),(75.3,120.5),(75.3,115.0),(63.3,115.0),(63.3,86.0),(75.3,86.0)]
K_ZONES=[dict(net_name='GND',layer='In4.Cu',points=OUTLINE,priority=0,clearance=0.25,min_width=0.2,pad_connection='solid',name='L5_GND_PLANE'),
         dict(net_name='GND',layer='In2.Cu',points=OUTLINE,priority=0,clearance=0.3,min_width=0.25,pad_connection='solid',name='L3_GND_FILL'),
         # VSYS to the buck on B.Cu, 3 mm band (charger->boost->buck island; the In3 front-left stays +3V3)
         dict(net_name='/charger/VSYS',layer='B.Cu',points=[(96.2,113.4),(119.6,113.4),(119.6,116.4),(96.2,116.4)],priority=2,clearance=0.25,min_width=0.25,pad_connection='solid',name='L6_VSYS_BUCK'),
]
K_MOVES=[dict(tool='rotate_component',reference='C716',angle=180),dict(tool='move_component',reference='C716',x=167.80,y=107.60),
         dict(tool='move_component',reference='U601',x=144.9,y=83.75)]
# ---- fix stage (goes into the SES): tracks/vias ----
W_USB=0.11
FIX_TRACKS=[
 # R904 Kelvin PVDD: B.Cu to a via beside the pad, F.Cu into the pad (from revb/design.py)
 dict(net=NETS['PVDD'],layer='B.Cu',x1=131.525,y1=96.9,x2=132.3,y2=96.9,w=0.25), dict(net=NETS['PVDD'],layer='F.Cu',x1=132.3,y1=96.9,x2=133.075,y2=96.9,w=0.3),
 dict(net=NETS['FB'],layer='B.Cu',x1=134.2,y1=96.9,x2=134.2,y2=96.05,w=0.2), dict(net=NETS['FB'],layer='F.Cu',x1=134.2,y1=96.05,x2=134.7,y2=96.55,w=0.2),
 # switch-pin stubs into their pours
 dict(net='/rails/BUCK_SW',layer='F.Cu',x1=104.74,y1=117.05,x2=105.9,y2=117.05,w=0.3),
 dict(net='/charger/CHG_SW2',layer='F.Cu',x1=167.45,y1=110.9,x2=167.45,y2=111.8,w=0.2),
 # C301 / C920 bulk-cap PVDD vias had no L1 link
]+[dict(net=NETS['PVDD'],layer='F.Cu',x1=a,y1=y,x2=c,y2=y,w=0.6) for a,c in ((142.4,143.6),(146.8,145.6)) for y in (99.3,100.6)]+[
 dict(net=NETS['PVDD'],layer='F.Cu',x1=142.5,y1=88.3,x2=143.4,y2=88.3,w=0.6),
 # C716 GND pad straight down to C707.2 / U701 pin 27
 dict(net='GND',layer='F.Cu',x1=167.025,y1=107.6,x2=167.03,y2=109.15,w=0.5),
 # USB: DP J601 -> U601.1 ; DN B.Cu jumper -> via -> U601.3 ; U601 -> CH340C as a coupled pair (DN north, DP south, pitch 0.26)
 dict(net=NETS['DP'],layer='F.Cu',x1=149.25,y1=82.6,x2=149.25,y2=84.6,w=W_USB), dict(net=NETS['DP'],layer='F.Cu',x1=149.25,y1=84.6,x2=148.95,y2=84.9,w=W_USB),
 dict(net=NETS['DP'],layer='F.Cu',x1=148.95,y1=84.9,x2=146.04,y2=84.9,w=W_USB),
 dict(net=NETS['DN'],layer='B.Cu',x1=149.75,y1=82.05,x2=147.0,y2=82.05,w=W_USB), dict(net=NETS['DN'],layer='F.Cu',x1=147.0,y1=82.05,x2=146.04,y2=82.80,w=W_USB),
]
_U6=144.9; _L=_U6-1.14   # U601 left pin column x
FIX_TRACKS+=[dict(net=NETS['DP'],layer='F.Cu',x1=146.04,y1=84.70,x2=_L,y2=84.70,w=W_USB),dict(net=NETS['DN'],layer='F.Cu',x1=146.04,y1=82.80,x2=_L,y2=82.80,w=W_USB)]   # flow-through under U601 (ST AN: pin1-pin6, pin3-pin4)
_PAIR=[  # (net, points) coupled pair U601 -> U201
 (NETS['DN'],[(_L,82.80),(142.2,82.80),(141.95,83.05),(141.95,84.69),(141.69,84.95),(126.17,84.95),(125.91,84.69),(125.91,82.08)]),
 (NETS['DP'],[(_L,83.75+0.95),(143.45,85.21),(124.9,85.21),(124.64,84.95),(124.64,82.08)])]
for n,P in _PAIR:
    for a,c in zip(P,P[1:]): FIX_TRACKS.append(dict(net=n,layer='F.Cu',x1=a[0],y1=a[1],x2=c[0],y2=c[1],w=W_USB))
FIX_TRACKS.append(dict(net='+3V3',layer='F.Cu',x1=143.76,y1=83.75,x2=142.6,y2=83.75,w=0.3))   # U601 pin 5 fan-out (new position)
FIX_VIAS=[dict(net='+3V3',x=142.6,y=83.75,size=0.6,drill=0.3),dict(net=NETS['PVDD'],x=132.3,y=96.9,size=0.5,drill=0.25), dict(net=NETS['FB'],x=134.2,y=96.05,size=0.5,drill=0.25),
 dict(net=NETS['DN'],x=147.0,y=82.05,size=0.45,drill=0.2),
 dict(net='GND',x=131.75,y=98.05,size=0.5,drill=0.25), dict(net='GND',x=130.8,y=98.65,size=0.5,drill=0.25),   # C914 ground
]
# more VSYS layer-change vias (>=12 per transition, LAYOUT_RULES §3): charger SYS band (Y 107.0) and boost VIN pour (Y 117.0/119.0 rows)
FIX_VIAS+=[dict(net=NETS['VSYS'],x=x,y=107.05,size=0.6,drill=0.3) for x in (170.3,172.5,176.9,179.1)]
FIX_VIAS+=[dict(net=NETS['VSYS'],x=x,y=117.0,size=0.6,drill=0.3) for x in (123.8,125.0,126.2,127.4,128.6)]
# A* jobs in the fix stage (net, src, dst, layers, width, clearance)
FIX_JOBS=[dict(net='/charger/CHG_SW1',src=(161.3,111.3),dst=(166.25,111.85),layers=['In3.Cu'],w=0.4,clr=0.25,name='BTST1_SW1_L4'),
          dict(net='/charger/CHG_SW2',src=(173.25,113.3),dst=(167.75,113.25),layers=['In3.Cu'],w=0.4,clr=0.25,name='BTST2_SW2_L4')]
# signal keep-out: charger SW1/SW2 link window (all layers) + 1 mm around switch-node copper
SW_WINDOW=(162.0,100.0,172.0,111.0)
# thermal landings: B.Cu exposed GND (mask opening), stitched; B.Cu signal routing kept out
LANDINGS={'U301':(103.0,90.1,116.4,105.1),'U401':(183.6,90.1,197.0,105.1),'U701':(171.5,117.6,180.4,120.4)}
LAND_NOTCH=[(111.95,91.2),(111.95,104.4),(188.05,91.2),(188.05,104.4)]   # PVDD vias at the amp pin-row ends: 1.6 mm square notches
def landing_poly(n):
    """box with 1.6 mm notches (open to the box edge) around the PVDD vias that sit within 1 mm of the top/bottom edge"""
    x0,y0,x1,y1=LANDINGS[n]; top=[(x0,y0)]; bot=[(x1,y1)]
    for x,y in sorted(LAND_NOTCH):
        if not (x0<x<x1): continue
        if abs(y-y0)<1.5: top+=[(x-0.8,y0),(x-0.8,y+0.8),(x+0.8,y+0.8),(x+0.8,y0)]
        if abs(y-y1)<1.5: bot=[(x+0.8,y1),(x+0.8,y-0.8),(x-0.8,y-0.8),(x-0.8,y1)]+bot[1:] if False else bot
    nb=[(x,y) for x,y in sorted(LAND_NOTCH,reverse=True) if x0<x<x1 and abs(y-y1)<1.5]
    B=[(x1,y1)]
    for x,y in nb: B+=[(x+0.8,y1),(x+0.8,y-0.8),(x-0.8,y-0.8),(x-0.8,y1)]
    return top+[(x1,y0)]+B+[(x0,y1)]
# ---- second native deletion set (before the SES import): U701 fan-out change + CC1 via clearance ----
DEL2=['013005e0-98da-4b4e-b185-6a9bb472c965','d3007844-5618-4b1e-b49d-31e30ad2d97e','c494f1b9-7436-4fbe-b74c-44fa9d422470','fe216948-c660-431a-ad17-02bafe694175',  # PROG via that boxed in INT/I2C
      'f12e2bf8-eff4-449d-8e28-fe4e8f05e5c6','fccd2981-bd3b-40b7-9f58-140bdef5868a',   # BAT_TS diagonal under pins 14/15 (blocks the I2C escape)
      '8a088205-90a5-4938-9fc3-bf1191dee031','74e62020-165e-49c0-b5d3-c625d7230264','4ff26d33-d0ba-4a37-a289-ebfb0f9facde']                                         # CC1 via 0.13 mm from J601 B7
FIX2_TRACKS=[dict(net='/usb_power/CC1',layer='F.Cu',x1=151.25,y1=80.72,x2=151.25,y2=81.62,w=0.2),dict(net='/usb_power/CC1',layer='B.Cu',x1=151.25,y1=81.62,x2=151.97,y2=82.34,w=0.2),
             dict(net='/usb_power/CC1',layer='B.Cu',x1=151.97,y1=82.34,x2=152.15,y2=82.34,w=0.2),
             dict(net='/charger/VBUS',layer='F.Cu',x1=163.3,y1=115.95,x2=163.78,y2=115.0,w=0.5)]   # rev A: charger VBUS L1<->L6 via never touched L1
FIX2_VIAS=[dict(net='/usb_power/CC1',x=151.25,y=81.62,size=0.45,drill=0.2)]
