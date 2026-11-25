import json,design6 as D
ops=[dict(tool='add_zone',**{**z,'points':[dict(x=x,y=y) for x,y in z['points']]}) for z in D.K_ZONES]+D.K_MOVES
json.dump(ops,open('k1ops.json','w'),indent=0); print(len(ops),'konnect ops')
