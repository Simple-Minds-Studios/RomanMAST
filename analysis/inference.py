import json, numpy as np
from scipy.optimize import least_squares, nnls
from lensbridge.point_lens import prepare,magnification
from pathlib import Path
import sys
G=prepare(json.loads(Path(sys.argv[1]).read_text())['rows'])
sets=[['OGLE'],['OGLE','KMTA','KMTC','KMTS'],['OGLE','KMTA','KMTC','KMTS','MOA']]
def solve(names,hold,positive):
 def evaluate(p, test=False):
  out=[]
  for n in names:
   t,f,e=G[n]; a=magnification(t,*p); X=np.column_stack([a,np.ones_like(a)]); mask=~hold(t); D=X[mask]/e[mask,None]; y=f[mask]/e[mask]; c=nnls(D,y)[0] if positive else np.linalg.lstsq(D,y,rcond=None)[0]; z=(f-X@c)/e
   if not test: out.extend(z[mask])
   elif n=='OGLE': return z[~mask]
  return np.array(out)
 fits=[least_squares(evaluate,[7560,u,te],bounds=([7510,.0001,.5],[7610,2,1000]),x_scale=[10,.1,50]) for u in [.01,.1,.5] for te in [10,50,150]]
 r=min((r for r in fits if r.success),key=lambda r:r.cost); z=evaluate(r.x,True); return dict(p=r.x.tolist(),n=len(z),chi2=float(z@z),train_chi2=float(2*r.cost))
res={}
for positive in [True,False]:
 key='nonnegative' if positive else 'signed'; res[key]={}
 for i,names in enumerate(sets):
  res[key]['ABC'[i]]=[solve(names,lambda t,k=k: (np.floor((t-7560)/2).astype(int)%5)==k,positive) for k in range(5)]
Path('results/E001_inference.json').write_text(json.dumps(res,indent=2))
for k,v in res.items():
 for n,rs in v.items(): print(k,n,sum(r['n'] for r in rs),sum(r['chi2'] for r in rs),np.array([r['p'] for r in rs]).min(0),np.array([r['p'] for r in rs]).max(0))
