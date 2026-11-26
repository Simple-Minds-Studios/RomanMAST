import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import scipy
from scipy.optimize import differential_evolution, nnls
import MulensModel as mm

ROOT=Path(__file__).resolve().parent
CONFIG=ROOT/'experiments/E003/config.json'

def atomic(path,obj):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False))
    tmp.replace(path)

def load(path,cfg):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=cfg['sha256']: raise ValueError('Input hash mismatch')
    d=json.loads(raw)
    if d['event_id']!=cfg['event'] or d['columns']!=['instrument','native_hjd_minus_2450000','magnitude','magnitude_error','source_record']: raise ValueError('Schema mismatch')
    groups={}
    for name,t,m,e,r in d['rows']: groups.setdefault(name,[]).append((float(t),float(m),float(e)))
    if {k:len(v) for k,v in groups.items()}!=cfg['counts']: raise ValueError('Count mismatch')
    groups.pop('Spitzer')
    for k,v in groups.items():
        t,m,e=np.array(sorted(v)).T
        if not np.isfinite([t,m,e]).all() or np.any(e<=0) or len(np.unique(t))!=len(t): raise ValueError(k)
        groups[k]=(t,m,e)
    return groups

def magnification(t,p):
    pars=dict(t_0=float(p[0]+2450000),u_0=float(p[1]),t_E=float(p[2]))
    if len(p)>=6: pars.update(q=float(10**p[3]),s=float(10**p[4]),alpha=float(p[5]%360))
    if len(p)==7: pars['rho']=float(10**p[6])
    model=mm.Model(pars)
    if len(p)==7: model.set_magnification_methods([float(t.min()+2449999),'VBM',float(t.max()+2450001)])
    a=model.get_magnification(t+2450000)
    if not np.isfinite(a).all() or np.any(a<=0): raise ValueError('Invalid magnification')
    return a

def split(t,fold,days=2,folds=5):
    return np.ones(len(t),dtype=bool) if fold<0 else (np.floor((t-7560)/days).astype(int)%folds)!=fold

def prepare(groups,fold,cfg):
    out={}
    for k,(t,m,e) in groups.items():
        train=split(t,fold,cfg['block_days'],cfg['folds'])
        if train.sum()<2: raise ValueError('Insufficient training data')
        f=10**(-.4*(m-np.median(m[train])))
        out[k]=(t,f,.4*np.log(10)*f*e,train)
    return out

def score(p,groups,details=False):
    try:
        result={}; total=0.
        for k,(t,f,e,train) in groups.items():
            a=magnification(t,p); X=np.column_stack((a,np.ones(len(t))))
            c=nnls(X[train]/e[train,None],f[train]/e[train])[0]
            z=(f-X@c)/e
            tr=float(z[train]@z[train]); te=float(z[~train]@z[~train])
            total+=tr
            if details: result[k]=dict(train_chi2=tr,test_chi2=te,n_train=int(train.sum()),n_test=int((~train).sum()),flux=c.tolist(),time=t.tolist(),residual=z.tolist(),train=train.tolist())
        return dict(train_chi2=total,test_chi2=sum(v['test_chi2'] for v in result.values()),instruments=result) if details else total
    except (ValueError,RuntimeError,ArithmeticError,np.linalg.LinAlgError):
        if details: raise
        return 1e30

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=ROOT.parent/'examples/public_data/data/1093.json')
    ap.add_argument('--mode',choices=['point','finite'],default='point')
    ap.add_argument('--fold',type=int,choices=range(-1,5),default=0)
    ap.add_argument('--seed',type=int,default=1093)
    ap.add_argument('--iterations',type=int,default=20)
    ap.add_argument('--population',type=int,default=6)
    ap.add_argument('--out',type=Path,default=ROOT/'results/E003')
    args=ap.parse_args()
    cfg=json.loads(CONFIG.read_text()); groups=prepare(load(args.input,cfg),args.fold,cfg)
    args.out.mkdir(parents=True,exist_ok=True)
    tag=f'{args.mode}_fold{args.fold}_seed{args.seed}_g{args.iterations}_p{args.population}'
    target=args.out/(tag+'.json')
    if target.exists(): raise FileExistsError(target)
    start=time.monotonic()
    def optimize(label,bounds):
        history=[]
        def callback(x,convergence):
            entry=dict(generation=len(history)+1,p=x.tolist(),train_chi2=float(score(x,groups)))
            history.append(entry)
            atomic(args.out/(tag+'_'+label+'_checkpoint.json'),history)
            print(label,entry,flush=True)
        r=differential_evolution(lambda p:score(p,groups),bounds,seed=args.seed,maxiter=args.iterations if label=='binary' else max(80,args.iterations),popsize=args.population,callback=callback,polish=True)
        if not np.isfinite(r.fun) or r.fun>=1e30: raise RuntimeError('No valid fit')
        return dict(p=r.x.tolist(),success=bool(r.success),message=str(r.message),nfev=int(r.nfev),population=r.population.tolist(),population_energies=r.population_energies.tolist(),**score(r.x,groups,True))
    single=optimize('single',cfg['bounds'][:3])
    binary=optimize('binary',cfg['bounds'][:7 if args.mode=='finite' else 6])
    report=dict(config=cfg,mode=args.mode,fold=args.fold,seed=args.seed,iterations=args.iterations,population=args.population,versions=dict(numpy=np.__version__,scipy=scipy.__version__,mulensmodel=mm.__version__),single=single,binary=binary,delta_train=single['train_chi2']-binary['train_chi2'],delta_test=single['test_chi2']-binary['test_chi2'] if args.fold>=0 else None,elapsed_seconds=time.monotonic()-start)
    atomic(target,report)
    print(target,'delta train',report['delta_train'],'delta test',report['delta_test'])
if __name__=='__main__': main()
