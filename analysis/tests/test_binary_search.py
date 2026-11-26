import numpy as np
import pytest
pytest.importorskip('MulensModel')
from binary_search import magnification, score, split

def test_single_analytic():
    t=np.linspace(7550,7570,100); p=[7560,.05,50]
    u=np.hypot(.05,(t-7560)/50)
    np.testing.assert_allclose(magnification(t,p),(u*u+2)/(u*np.sqrt(u*u+4)),rtol=1e-8)

@pytest.mark.parametrize('p',[[7560,.05,50,-3,.08,45],[7560,.05,50,-3,.08,45,-3]])
def test_binary_synthetic(p):
    t=np.linspace(7550,7570,200); a=magnification(t,p)
    train=split(t,0); e=np.full(len(t),.01); f=2*a+.3
    g={'synthetic':(t,f,e,train)}
    r=score(p,g,True)
    assert r['train_chi2']<1e-12 and r['test_chi2']<1e-12
    assert score([7560,.05,50],g)>1
    f2=f.copy(); f2[~train]+=100
    r2=score(p,{'synthetic':(t,f2,e,train)},True)
    np.testing.assert_allclose(r['instruments']['synthetic']['flux'],r2['instruments']['synthetic']['flux'])
    assert r2['test_chi2']>r['test_chi2']

def test_partitions():
    t=np.linspace(7540,7580,501)
    assert np.all(sum(~split(t,k) for k in range(5))==1)
