"""SES writer: tracks/vias dicts (KiCad mm) -> Specctra session (0.1 um units, y negated). Via padstacks per (size,drill) through all copper."""
def write(path,tracks,vias,layers):
    U=lambda v: int(round(v*10000))
    ps={}
    for v in vias: ps[(v['size'],v['drill'])]='Via[0-%d]_%d:%d_um'%(len(layers)-1,round(v['size']*1000),round(v['drill']*1000))
    by={}
    for t in tracks: by.setdefault(t['net'],[[],[]])[0].append(t)
    for v in vias: by.setdefault(v['net'],[[],[]])[1].append(v)
    o=['(session "revb"','  (base_design "revb")','  (routes','    (resolution um 10)','    (parser (host_cad "KiCad\'s Pcbnew") (host_version "10"))','    (library_out']
    for (s,d),n in ps.items():
        o.append('      (padstack "%s"'%n)
        for l in layers: o.append('        (shape (circle %s %d 0 0))'%(l,U(s)))
        o.append('        (attach off)\n      )')
    o.append('    )\n    (network_out')
    for net,(T,V) in by.items():
        o.append('      (net "%s"'%net)
        for t in T: o.append('        (wire (path %s %d %d %d %d %d))'%(t['layer'],U(t['w']),U(t['x1']),-U(t['y1']),U(t['x2']),-U(t['y2'])))
        for v in V: o.append('        (via "%s" %d %d)'%(ps[(v['size'],v['drill'])],U(v['x']),-U(v['y'])))
        o.append('      )')
    o.append('    )\n  )\n)\n'); open(path,'w').write('\n'.join(o))
