import json, sys, hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
from lensbridge.point_lens import prepare, fit, magnification

def run(path):
 raw=Path(path).read_bytes(); g=prepare(json.loads(raw)['rows']); g.pop('Spitzer'); rng=np.random.default_rng(1093)
 sets=[['OGLE'],['OGLE','KMTA','KMTC','KMTS'],list(g)]
 out={'sha256':hashlib.sha256(raw).hexdigest(),'runs':{},'synthetic':[]}
 for label,names in zip('ABC',sets):
  groups={n:g[n] for n in names}; r=fit(groups,7560); p=[r[k] for k in ('t0','u0','te')]; scales={}; diag={}
  for n,(t,f,e) in groups.items():
   X=np.column_stack((magnification(t,*p),np.ones(len(t)))); c=nnls(X/e[:,None],f/e)[0]; z=(f-X@c)/e; z=z[np.argsort(t)]; scales[n]=max(1,float(np.sqrt(np.mean(z*z)))); diag[n]={'rms':float(np.sqrt(np.mean(z*z))),'adjacent_correlation':float(np.corrcoef(z[:-1],z[1:])[0,1])}
  weighted={n:(t,f,e*scales[n]) for n,(t,f,e) in groups.items()}; w=fit(weighted,7560)
  out['runs'][label]={'baseline':r,'rescaled':w,'scales':scales,'diagnostics':diag}
 for i in range(20):
  t=np.linspace(-100,100,401); a=magnification(t,2,.2,35); groups={n:(t,s*a+b+rng.normal(0,e,len(t)),np.full_like(t,e)) for n,s,b,e in [('A',2,.3,.03),('B',.7,1.2,.04)]}; out['synthetic'].append(fit(groups,0))
 return out
if __name__=='__main__':
 print(json.dumps(run(sys.argv[1]),indent=2))
