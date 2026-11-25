from blk_common import *
N=dict(NET,DO='/battery/PROT_DO',CO='/battery/PROT_CO',VM='/battery/PROT_VM')
T=[];V=[];Z=[];J=[]; t,v,z,j=mk(T,V,Z,J,N)
# PACK_P: J801 pin2 -> F801 pad1 on L1+L3+L4 (pack current 7 A cont / 10 A pk; IPC-2221 needs ~2.9 mm on 1 oz)
pk=[(212.4,90.2),(222.6,90.2),(222.6,105.0),(217.5,105.0),(217.5,101.6),(216.6,99.4),(216.6,94.2),(212.4,94.2)]
for l in ('F.Cu','In2.Cu','B.Cu'): z('PACKP',l,pk,clr=0.25,name='PACK_P_'+l[:3],keep=(l=='F.Cu'))
for x,y in [(218.2,101.9),(219.3,101.9),(220.4,101.9),(221.6,102.7),(221.6,103.8),(217.8,92.0),(219.0,92.0),(220.2,92.0),(221.4,92.0)]: v('PACKP',x,y)
# BATT_N island (never GND): J801 pin1 -> Q801 source; copper on L1/L3/L4 for Q801 1.5 W (S3)
bn=[(210.6,95.2),(216.3,95.2),(216.3,102.75),(213.7,102.75),(213.7,101.35),(210.6,101.35)]
for l in ('F.Cu','In2.Cu','B.Cu'): z('BATTN',l,bn,clr=0.3,name='BATT_N_'+l[:3],keep=(l=='F.Cu'))
for x,y in [(211.2,96.2),(211.2,97.6),(211.2,99.0),(211.2,100.5),(212.4,100.6),(213.4,100.6),(214.4,100.7),(215.5,100.7)]: v('BATTN',x,y)
# PROT_D common-drain pour (Q801/Q802 drain tabs) L1/L3/L4 + thermal vias
pd=[(210.9,103.2),(216.6,103.2),(216.6,109.0),(210.9,109.0)]
z('PROTD','F.Cu',[(212.9,103.0),(215.8,103.0),(215.8,109.1),(212.9,109.1)],clr=0.25,name='PROT_D_F',keep=True)
for l in ('In2.Cu','B.Cu'): z('PROTD',l,pd,clr=0.3,name='PROT_D_'+l[:3])
for x,y in [(213.4,105.6),(214.3,105.6),(215.2,105.6),(213.4,106.5),(214.3,106.5),(215.2,106.5)]: v('PROTD',x,y)
# Q802 source -> GND with via array
z('GND','F.Cu',[(212.3,109.55),(214.95,109.55),(214.95,111.4),(212.3,111.4)],name='Q802_SRC_GND')
for x in (212.7,213.6,214.5): v('GND',x,111.0)
# VBAT_PACK: F801 pad2 -> L3/L4 plane to Q701 drain
z('VBATP','F.Cu',[(217.5,107.1),(221.0,107.1),(221.0,110.35),(217.5,110.35)],name='VBAT_F801',keep=True)
for x in (217.9,218.9,219.9,220.7): v('VBATP',x,110.0)
vb=[(180.6,111.2),(209.7,111.2),(209.7,109.6),(217.2,109.6),(221.3,109.6),(221.3,120.4),(180.6,120.4)]
for l in ('In2.Cu','B.Cu'): z('VBATP',l,vb,pri=1,clr=0.3,name='VBAT_PACK_'+l[:3])
z('VBATP','F.Cu',[(178.25,112.55),(181.7,112.55),(181.7,115.4),(178.25,115.4)],name='Q701_DRAIN',keep=True)
for y in (112.95,113.95,114.95): v('VBATP',181.25,y)
# gate drives + Kelvin V- sense (R803 returns at the Q802 source / GND junction, spec_power 6)
j('DO',(208.66,112.65),(213.33,102.26),layers=['F.Cu','B.Cu'],via=(0.45,0.2),w=0.25,res=0.05,clr=0.15,margin=3)
j('CO',(208.66,113.6),(215.27,109.94),layers=['F.Cu','B.Cu'],via=(0.45,0.2),w=0.25,res=0.05,clr=0.15,margin=3)
j('GND',(211.42,110.4),(212.7,111.0),w=0.3,name='R803_kelvin_to_Q802_src')
