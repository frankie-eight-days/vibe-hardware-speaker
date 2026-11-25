# Keep in the DSN network only nets with open connections: the open pins, or every pin when an open item is a track/via/zone.
import json,re,sys
def reduce(drcj,dsn):
    d=json.load(open(drcj)); need={}; full=set()
    for u in d['unconnected_items']:
        for it in u['items']:
            m=re.match(r'(?:PTH )?[Pp]ad (\S+) \[([^\]]+)\] of (\S+)',it['description'])
            if m: need.setdefault(m.group(2),set()).add(f"{m.group(3)}-{m.group(1)}")
            else:
                n=re.search(r'\[([^\]]+)\]',it['description'])
                if n: full.add(n.group(1))
    POW=('GND','PVDD','VSYS','VBUS','VBAT_PACK','BATT_N','PACK_P','CHG_BAT','CHG_SW1','CHG_SW2','PROT_D','CHG_PMID')
    full={n for n in full if not any(n.endswith(q) for q in POW)}
    start=dsn.index('  (network')
    net_re=re.compile(r'    \(net (\S+)\n      \(pins ([^)]*)\)\n    \)\n',re.S)
    kept=[]
    def repl(m):
        name=m.group(1).strip('"'); pins=m.group(2).split()
        if name in full: keep=pins
        elif name in need: keep=[p for p in pins if p.split('@')[0] in need[name]]
        else: return ''
        if len(keep)<2 and name not in full: return ''
        kept.append(name); return f"    (net {m.group(1)}\n      (pins {' '.join(keep)})\n    )\n"
    body=net_re.sub(repl,dsn[start:])
    return dsn[:start]+body,kept,full
