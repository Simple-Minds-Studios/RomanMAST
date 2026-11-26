import numpy as np
from lensbridge.point_lens import magnification, fit

def test_synthetic_recovery():
    t=np.linspace(-100,100,401)
    a=magnification(t,2,.2,35)
    groups={"A":(t,2*a+.3,np.full_like(t,.01)),"B":(t,.7*a+1.2,np.full_like(t,.02))}
    r=fit(groups,0)
    np.testing.assert_allclose([r["t0"],r["u0"],r["te"]],[2,.2,35],rtol=1e-4,atol=1e-4)

def test_satellite_rejected():
    import pytest
    with pytest.raises(ValueError):
        fit({"Spitzer":None},0)
