NET={'GND':'GND','PVDD':'/amp_left/PVDD','VSYS':'/charger/VSYS','VBUS':'/charger/VBUS','PMID':'/charger/CHG_PMID','SW1':'/charger/CHG_SW1','SW2':'/charger/CHG_SW2',
 'BAT':'/charger/CHG_BAT','VBATP':'/battery/VBAT_PACK','PACKP':'/battery/PACK_P','BATTN':'/battery/BATT_N','PROTD':'/battery/PROT_D','3V3':'+3V3'}
def mk(T,V,Z,J,N):
    def t(n,l,pts,w):
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]): T.append(dict(net=N.get(n,n),layer=l,x1=x1,y1=y1,x2=x2,y2=y2,w=w))
    def v(n,x,y,d=0.6,dr=0.3): V.append(dict(net=N.get(n,n),x=x,y=y,size=d,drill=dr))
    def z(n,l,pts,pri=3,clr=0.2,conn='solid',name=None,keep=False,minw=0.2): Z.append(dict(net=N.get(n,n),layer=l,pts=pts,priority=pri,clearance=clr,pad_connection=conn,name=name,min_width=minw,keep=keep))
    def j(n,src,dst,**k): J.append(dict(net=N.get(n,n),src=src,dst=dst,name=k.pop('name',n),**k))
    return t,v,z,j
