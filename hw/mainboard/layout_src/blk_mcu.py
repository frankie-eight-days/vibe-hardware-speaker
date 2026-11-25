from blk_common import *
import geom, place
P=place.P
def pp(ref,num): p=[q for q in geom.pads(ref,P) if q['num']==num][0]; return (round(p['x'],4),round(p['y'],4))
N=dict(NET,EN='/mcu/ESP_EN',IO0='/mcu/ESP_IO0',BEN='/mcu/BOOST_EN',PDN='/AMP_PDN',IO26='/mcu/IO26_R',BCLKM='/mcu/I2S_BCLK_MCU',BCLK='/I2S_BCLK',
       IO18='/mcu/IO18_R',SCLK='/mcu/LCD_SCLK',IO32='/mcu/IO32_R',PDMCLK='/mcu/PDM_CLK',IO5='/mcu/IO5_R',IO15='/mcu/IO15_R')
T=[];V=[];Z=[];J=[]; t,v,z,j=mk(T,V,Z,J,N)
F2=dict(layers=['F.Cu','B.Cu'],via=(0.45,0.2),res=0.025,clr=0.2)
# 3V3 at module pin 2: C102 (100 nF) first, C101 (22 uF) behind it; GND vias at the cap pads (spec_signal 1.6)
j('3V3',pp('U101','2'),pp('C102','1'),w=0.4,res=0.025,clr=0.15,name='3V3_pin2_C102')
j('3V3',pp('C102','1'),pp('C101','1'),w=0.4,res=0.025,clr=0.15,name='3V3_C102_C101',margin=1.5)
v('3V3',65.6,111.55); t('3V3','F.Cu',[pp('C101','1'),(65.6,111.55)],0.5)
v('GND',65.3,110.15,0.5,0.25); t('GND','F.Cu',[pp('C102','2'),(65.3,110.15)],0.3)
v('GND',65.6,113.35); t('GND','F.Cu',[pp('C101','2'),(65.6,113.35)],0.5)
# module EPAD -> L2 GND (WROVER-E Fig.15: vias in the gaps between the 9 sub-pads)
for x in (70.035,71.435):
    for y in (98.8,100.2): v('GND',x,y,0.5,0.25)
j('IO26',pp('U101','11'),pp('R110','1'),w=0.2,name='IO26_R110',**F2)
j('IO18',pp('U101','30'),pp('R113','1'),w=0.2,name='IO18_R113',margin=4,**F2)
j('IO32',pp('U101','8'),pp('R118','1'),w=0.2,name='IO32_R118',**F2)
# strapping lines (EN/IO0/IO2/IO12/IO5/IO15): short, direct to their pull resistors
j('EN',pp('U101','3'),pp('C103','1'),w=0.25,name='EN_pin_to_RC',margin=4,layers=['F.Cu','B.Cu'],via=(0.45,0.2),res=0.05,clr=0.2,maxit=5000000)
j('EN',pp('R101','2'),pp('C103','1'),w=0.25,name='EN_R101',**F2)
j('EN',pp('Q201','3'),pp('C103','1'),w=0.25,name='EN_Q201',**F2)
j('IO0',pp('U101','25'),pp('R102','2'),w=0.25,name='IO0_pin_R102',**F2)
j('IO0',pp('R102','2'),pp('Q202','3'),w=0.25,name='IO0_Q202',margin=3,**F2)
j('BEN',pp('U101','24'),pp('R107','2'),w=0.25,name='IO2_R107',**F2)
j('PDN',pp('U101','14'),pp('R108','2'),w=0.25,name='IO12_R108',**F2)
j('IO5',pp('U101','29'),pp('R115','1'),w=0.2,name='IO5_R115',margin=4,**F2)
j('IO15',pp('U101','23'),pp('R116','1'),w=0.2,name='IO15_R116',margin=2.5,**F2)
# clocks with the series R at the source
j('BCLKM',pp('R110','2'),pp('R505','1'),w=0.2,res=0.1,clr=0.25,layers=['F.Cu','B.Cu'],via=(0.45,0.2),win=(73,104,121,121),name='BCLK_MCU_to_R505')
j('BCLK',pp('R505','2'),pp('U301','7'),w=0.2,res=0.05,clr=0.25,layers=['F.Cu','B.Cu'],via=(0.45,0.2),margin=3,name='BCLK_R505_U301')
j('SCLK',pp('R113','2'),pp('J501','5'),w=0.2,res=0.1,clr=0.25,layers=['F.Cu','B.Cu'],via=(0.45,0.2),win=(84,75.4,233,88.5),name='LCD_SCLK_to_J501',maxit=6000000)
