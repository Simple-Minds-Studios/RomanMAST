"""Exploratory point-source point-lens model; no parallax or finite source."""
import numpy as np
from scipy.optimize import least_squares, nnls

def magnification(t, t0, u0, te):
    u = np.hypot(u0, (np.asarray(t)-t0)/te)
    return (u*u+2)/(u*np.sqrt(u*u+4))

def prepare(rows):
    groups = {}
    for instrument,t,m,e,record in rows:
        groups.setdefault(instrument, []).append((float(t),float(m),float(e)))
    result = {}
    for name, values in groups.items():
        t,m,e = np.asarray(values).T
        if not np.isfinite([t,m,e]).all() or np.any(e<=0):
            raise ValueError("Invalid photometry: "+name)
        f = 10**(-0.4*(m-np.median(m)))
        result[name] = (t,f,np.log(10)*0.4*f*e)
    return result

def residuals(p, groups):
    t0,u0,te = p
    out = []
    for t,f,e in groups.values():
        a = magnification(t,t0,u0,te)
        design = np.column_stack((a,np.ones_like(a)))
        coeff = nnls(design/e[:,None],f/e)[0]
        out.append((f-design@coeff)/e)
    return np.concatenate(out)

def fit(groups, peak):
    if not groups or "Spitzer" in groups:
        raise ValueError("Ground-based series only")
    bounds = ([peak-50,0.0001,0.5],[peak+50,2,1000])
    trials = [least_squares(residuals,[peak,u,te],bounds=bounds,args=(groups,),x_scale=[10,.1,50]) for u in [.01,.1,.5] for te in [10,50,150]]
    good = [r for r in trials if r.success and np.isfinite(r.cost)]
    if not good:
        raise RuntimeError("No converged fit")
    r = min(good,key=lambda r:r.cost)
    return dict(t0=float(r.x[0]),u0=float(r.x[1]),te=float(r.x[2]),chi2=float(2*r.cost),n=int(len(r.fun)),converged_starts=len(good),total_starts=len(trials),boundary=bool(np.any(r.active_mask)),model="PSPL, nonnegative source and blend flux; no parallax")
