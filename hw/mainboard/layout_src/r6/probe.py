import pcbnew
print([m for m in dir(pcbnew) if 'STACK' in m.upper()][:40])
ds=pcbnew.BOARD_DESIGN_SETTINGS
print([m for m in dir(ds) if 'tack' in m or 'Board' in m][:40])
