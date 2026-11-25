"""Rigid power blocks: footprints + critical copper (spec_critical/spec_fanout items), by UUID."""
import sys,json,pcbnew
mm=pcbnew.ToMM
def rng(p,a,b,ex=()): return [f'{p}{i}' for i in range(a,b+1) if f'{p}{i}' not in ex]
BLOCKS={
 'AMP_L': ['U301']+rng('C',302,319)+rng('L',301,304),
 'AMP_R': ['U401']+rng('C',402,419)+rng('L',401,404),
 'BOOST': ['U901','L901']+rng('C',901,916)+rng('R',901,907),
 'BUCK':  ['U951','L951']+rng('C',951,959)+rng('R',951,955),
 'CHG':   ['U701','L701','Q701']+rng('C',701,718),
 'BATT':  ['J801','F801','Q801','Q802','R803'],
}
GLOBAL_Z={'L6_VSYS_BUCK','L5_GND_PLANE','L2_GND_SOLID','L1_GND_POUR','L4_GND_POUR','L3_GND_FILL','L3_PVDD','L3_VSYS','L3_3V3','VBAT_PACK_In2','VBAT_PACK_B.C','USB_VBUS_L4','USB_VBUS_R','USB_VBUS_L'}
CLIP={'BOOST_VOUT_PVDD':'BOOST'}   # distribution pour clipped to the block box
if __name__=='__main__':
    b=pcbnew.LoadBoard(sys.argv[1])
    L='/Users/frankwalsh/Documents/vibecoding/anthropic_hardware_test/hw/mainboard/layout_src/'
    specs=[json.load(open(L+f)) for f in ('spec_critical.json','spec_fanout.json')]
    key=lambda x,y:(round(x,2),round(y,2))
    VK={key(v['x'],v['y']) for s in specs for v in s['vias']}
    ST={key(v['x'],v['y']) for v in json.load(open(L+'spec_stitch.json'))['vias']}   # GND stitching (rings around the switchers)
    TK=set()
    for s in specs:
        for t in s['tracks']: TK|={(key(t['x1'],t['y1']),key(t['x2'],t['y2'])),(key(t['x2'],t['y2']),key(t['x1'],t['y1']))}
    fps={f.GetReference():f for f in b.GetFootprints()}
    out={}
    for name,refs in BLOCKS.items():
        nets=set(); bb=None
        for r in refs:
            f=fps[r]; nets|={p.GetNetname() for p in f.Pads()}
            c=f.GetCourtyard(pcbnew.F_CrtYd).BBox()
            x=[mm(c.GetX()),mm(c.GetY()),mm(c.GetRight()),mm(c.GetBottom())]
            bb=x if bb is None else [min(bb[0],x[0]),min(bb[1],x[1]),max(bb[2],x[2]),max(bb[3],x[3])]
        nets.discard('')
        out[name]=dict(refs=refs,nets=sorted(nets),fpbox=bb,items=[])
    PADS={name:[(p.GetNetname(),mm(p.GetX()),mm(p.GetY())) for r in B['refs'] for p in fps[r].Pads()] for name,B in out.items()}
    PFX={'BOOST':'BOOST','CHG':'CHG','BUCK':'BUCK','PACK':'BATT','BATT':'BATT','PROT':'BATT','Q802':'BATT','VBAT_F801':'BATT','Q701':'CHG','PVDD_U301':'AMP_L','GND_U301':'AMP_L','PVDD_U401':'AMP_R','GND_U401':'AMP_R'}
    def inbox(bb,x,y,g=0.6): return bb[0]-g<=x<=bb[2]+g and bb[1]-g<=y<=bb[3]+g
    owner={}
    for t in b.GetTracks():
        n=t.GetNetname()
        ends=[]
        if t.GetClass()=='PCB_VIA':
            k_=key(mm(t.GetX()),mm(t.GetY()))
            if k_ not in VK and k_ not in ST: continue
            x,y=mm(t.GetX()),mm(t.GetY())
            if k_ in ST:
                hit=[nm for nm,B in out.items() if inbox(B['fpbox'],x,y,0.3)]
                if hit: out[hit[0]]['items'].append(t.m_Uuid.AsString()); out[hit[0]]['stitch']=out[hit[0]].get('stitch',0)+1
                continue
        else:
            s,e=t.GetStart(),t.GetEnd()
            if (key(mm(s.x),mm(s.y)),key(mm(e.x),mm(e.y))) not in TK: continue
            x,y=(mm(s.x)+mm(e.x))/2,(mm(s.y)+mm(e.y))/2
            ends=[(mm(s.x),mm(s.y)),(mm(e.x),mm(e.y))]
        best=None
        for name,B in out.items():
            if n in B['nets'] and inbox(B['fpbox'],x,y,1.0) and (t.GetClass()=='PCB_VIA' or all(inbox(B['fpbox'],*p,0.6) for p in ends)):
                d=min(((x-px)**2+(y-py)**2) for (pn,px,py) in PADS[name] if pn==n)
                if best is None or d<best[0]: best=(d,name)
        if best: out[best[1]]['items'].append(t.m_Uuid.AsString())
    for z in b.Zones():
        nm=z.GetZoneName()
        if nm in GLOBAL_Z: continue
        bx=z.GetBoundingBox(); x,y=mm(bx.Centre().x),mm(bx.Centre().y)
        hit=next((v for k,v in PFX.items() if nm.startswith(k)),None)
        if hit: out[hit]['items'].append(z.m_Uuid.AsString()); out[hit].setdefault('zones',[]).append(nm)
        else: print('unassigned zone',nm)
    # full box incl copper
    byid={}
    for t in b.GetTracks(): byid[t.m_Uuid.AsString()]=t
    for z in b.Zones(): byid[z.m_Uuid.AsString()]=z
    for name,B in out.items():
        bb=list(B['fpbox'])
        for u in B['items']:
            it=byid[u]
            if it.GetClass()=='ZONE' and it.GetZoneName() in CLIP: continue
            c=it.GetBoundingBox(); x=[mm(c.GetX()),mm(c.GetY()),mm(c.GetRight()),mm(c.GetBottom())]
            bb=[min(bb[0],x[0]),min(bb[1],x[1]),max(bb[2],x[2]),max(bb[3],x[3])]
        B['box']=[round(v,2) for v in bb]
        print(name,'stitch',B.get('stitch',0),len(B['refs']),'items',len(B['items']),'fpbox',[round(v,1) for v in B['fpbox']],'box',B['box'],'%.0fx%.0f'%(bb[2]-bb[0],bb[3]-bb[1]),B.get('zones'))
    json.dump(out,open('blocks.json','w'),indent=0)
