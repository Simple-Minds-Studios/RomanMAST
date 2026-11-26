# E003.1 synthetic diagnostic controls

These nine reports were generated with the published E003.1 forward model and
objective at `48361288e0c574de0cadb50c55515c5dc5d8ba05` in bartOS. The
observational catalog supplied sample times only. Full and reduced cadence use
the published 1.5% independent Gaussian flux noise and seed 3329. They generate
noise separately on their respective time grids, so their residuals are not
paired. The reduced series uses every 30th sample per instrument. The first
reduced injection reproduces the published smoke generator and uses the same
flux errors and training window. The dense series is noiseless, with fine
sampling near the injected peak and wider coverage in the wings.

Each local control starts at the known seven-parameter truth, profiles
nonnegative source and blend fluxes with the published objective, and is
limited to 30 reported least-squares function evaluations. This is a
truth-started check, not a blind recovery experiment. Numerical optimizer
success and satisfying the frozen parameter tolerances are recorded separately.
The noiseless controls use the same forward model to generate and fit data.

To reproduce from the published LensBridge repo root with bartOS active, set
`CONTROLS_DIR` to the absolute directory containing this README and use a fresh
report directory.

```sh
mkdir synthetic-control-reproduction
PYTHONPATH="$PWD/analysis" MPLBACKEND=Agg python "$CONTROLS_DIR/run_controls.py" synthetic-control-reproduction
```
