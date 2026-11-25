import sys,numpy as np,pcbnew
sys.path.insert(0,'/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src'); import arouter
b=pcbnew.LoadBoard('t2.kicad_pcb')
for net,(x,y) in (('/I2C_SDA',(168.0,115.6)),('/charger/CHG_INT',(169.6,112.15)),('/charger/CHG_INT',(170.9,112.25))):
    R=arouter.Router(b,(x-1,y-1,x+1,y+1),res=0.05,layers=('F.Cu',))
    i=int(round((x-R.x0)/R.res)); j=int(round((y-R.y0)/R.res)); hits=[]
    for l in R.all:
        for kind,n,g in R.items[l]:
            if n==net: continue
            R2=R.items[l]; 
        B=R.blocked(l,net,0.225+0.15)
        if B[j,i]: hits.append(l)
    print(net,(x,y),'via blocked on',hits)
    for l in hits:
        for kind,n,g in R.items[l]:
            if n==net: continue
            saved=R.items[l]; R.items[l]=[(kind,n,g)]
            if R.blocked(l,net,0.375)[j,i]: print('   ',l,kind,n[-12:])
            R.items[l]=saved
