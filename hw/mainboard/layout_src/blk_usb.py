from blk_common import *
import geom, place
P=place.P
def pp(ref,num): p=[q for q in geom.pads(ref,P) if q['num']==num][0]; return (round(p['x'],4),round(p['y'],4))
N=dict(NET,DP='/usb_power/USB_DP',DN='/usb_power/USB_DN',CC1='/usb_power/CC1',CC2='/usb_power/CC2')
T=[];V=[];Z=[];J=[]; t,v,z,j=mk(T,V,Z,J,N)
# VBUS: receptacle VBUS pads -> vias -> L4 band -> charger VBUS bulk; TVS D601 right at the VBUS pads
z('VBUS','F.Cu',[(152.15,80.0),(152.75,80.0),(152.75,81.5),(153.5,82.3),(153.5,84.9),(151.95,84.9),(151.95,82.0),(152.15,81.5)],name='USB_VBUS_R',keep=True)
z('VBUS','F.Cu',[(147.25,80.0),(147.85,80.0),(147.85,81.5),(147.95,82.2),(147.95,84.1),(146.65,84.1),(146.65,82.2),(147.25,81.5)],name='USB_VBUS_L',keep=True)
for x,y in [(152.55,83.0),(152.55,84.0),(147.3,83.6)]: v('VBUS',x,y)
z('VBUS','B.Cu',[(146.6,83.0),(153.8,83.0),(160.2,87.2),(160.2,115.7),(157.4,115.7),(157.4,88.2),(152.8,85.2),(146.6,85.2)],pri=3,name='USB_VBUS_L4',keep=True)
v('GND',156.5,83.55); t('GND','F.Cu',[(155.6,84.0),(156.5,83.55)],0.5)
# data pair, hand-routed: DP joined on L1 under the pads, DN joined by an L4 jumper and run on L4 under the DP, both through U601 (flow-through ESD) to CH340C
v('DN',149.75,82.05,0.45,0.2); v('DN',150.75,82.05,0.45,0.2)
t('DN','F.Cu',[(149.75,81.4),(149.75,82.05)],0.2); t('DN','F.Cu',[(150.75,81.4),(150.75,82.05)],0.2)
t('DN','B.Cu',[(150.75,82.05),(149.75,82.05),(144.0,82.05)],0.28); v('DN',144.0,82.05,0.45,0.2); t('DN','F.Cu',[(144.0,82.05),(143.9,82.65),(143.34,82.65)],0.28)
t('DP','F.Cu',[(149.25,81.4),(149.25,82.6),(150.25,82.6),(150.25,81.4)],0.2)
t('DP','F.Cu',[(149.25,82.6),(149.25,84.9),(144.3,84.9),(143.95,84.55),(143.34,84.55)],0.28)
for n,pin_esd_out,pin_ch in (('DN','4','6'),('DP','6','5')):
    j(n,pp('U601',pin_esd_out),pp('U201',pin_ch),w=0.28,res=0.025,clr=0.15,name=n+'_esd_ch340',margin=2,layers=['F.Cu'])
# CC2 escapes through L3 (boxed in by VBUS and the DP join)
v('CC2',148.6,83.7,0.45,0.2); t('CC2','F.Cu',[(148.25,81.4),(148.25,83.35),(148.6,83.7)],0.2)
j('CC2',(148.6,83.7),pp('U602','3'),layers=['In2.Cu','F.Cu'],start='In2.Cu',end=['F.Cu'],via=(0.45,0.2),w=0.2,res=0.05,clr=0.15,margin=3,name='CC2_L3')
# CC lines: receptacle -> ESD U602 -> CH224Q
j('CC1',pp('J601','A5'),pp('U602','1'),layers=['F.Cu','B.Cu'],via=(0.45,0.2),w=0.2,res=0.025,clr=0.13,margin=2)
j('CC1',pp('U602','6'),pp('U603','7'),layers=['F.Cu','B.Cu'],via=(0.45,0.2),w=0.2,res=0.025,clr=0.13,margin=2,name='CC1b')
j('CC2',pp('U602','4'),pp('U603','6'),layers=['F.Cu','B.Cu'],via=(0.45,0.2),w=0.2,res=0.025,clr=0.13,margin=2,name='CC2b')
