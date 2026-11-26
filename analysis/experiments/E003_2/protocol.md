# E003.2 Parameter Identifiability and Global Recovery Validation

E003.2-v1 is a synthetic-only diagnostic benchmark. Use the pinned E003.1
bartOS dependencies. From the repository's analysis directory, run:

```sh
MPLBACKEND=Agg python synthetic_validation.py --out results/E003_2/v1-reproduction
```

Use a new output directory for every attempt. The existing output directory
guard protects both completed and interrupted evidence. The manifest records
the configured settings, effective grids and dataset sizes, dataset hashes,
input file hashes, implementation hashes and library versions. Each blind run
records its effective population, actual evaluations and generations, elapsed
time and convergence trace. Local histories include residual calls used to
estimate derivatives. Elapsed times vary between machines.

## Designs and interpretation

- Full historical cadence supplies sample times only. Every 30th row per
  instrument is selected with its original simulated observed flux, error and
  holdout membership. The reduced grid has no observations in the configured
  historical-time holdout window and its predictive χ² is recorded as null.
- Dense injection runs use the same grid for every injection, independent of
  the injected truth, with a fixed interleaved holdout mask. Differential
  evolution starts from a Latin hypercube across the full bounds, with no
  truth-derived initial candidate. Each seed and budget has a separate report.
- Profiles fix one coordinate and reoptimize the six other geometric
  parameters and per-instrument source and blend coefficients. Each grid
  point starts once from the truth and once from the best dense blind fit.
  The plotted sampled minima are conditional on the grid and search budget.
  Inspect termination flags before interpreting a shallow or irregular profile.
  Jacobian correlations and singular values describe the local profiled
  objective and can be unreliable near boundaries and unidentified directions.
- For injection 3, rerun the truth-started fit from the same initial point
  with 30 and 100 evaluations on each matched grid. Compare terminal
  objective, optimality, bound activity and tolerance failures.
- Close and wide controls use the injected geometry and its reciprocal
  separation as starts in distinct constrained fits. Under the separate,
  provisional E003.2-v1 waveform criterion, a candidate is equivalent only
  if the RMS difference in predictions is at most 0.05 input-error units on
  both training and holdout points. This checks equivalence for the sampled
  trajectories, not the existence of all possible physical degeneracies.
  It does not turn a frozen E003.1 parameter failure into a pass.
- Each null injects a single lens with independent Gaussian noise. The
  provisional screen requires a binary training Δχ² of at least 25 and
  positive predictive Δχ² relative to a locally refined single lens. The
  threshold is a pilot diagnostic choice and is not a calibrated detection
  rule. Both model fits use training observations only. Six noise
  realizations at one geometry give a broad exact binomial interval and do
  not estimate behavior across the historical event population.

The frozen E003.1 parameter tolerances and injection vectors are loaded unchanged.
Successful exact recovery is reported separately from waveform equivalence and
optimizer termination. The pilot budgets and null controls are insufficient to
certify global recovery or establish a scientific detection threshold. Keep
historical planetary recovery paused until a separately frozen protocol
establishes blind recovery and null-control acceptance criteria and passes them.

The separate replay below uses the archived E003.1 per-instrument objective and
original Gaussian noise streams. It reproduces the original 30-evaluation
control before comparing a 100-evaluation budget without changing the original
results. Run it from the analysis directory.

```sh
PYTHONPATH="$PWD" python experiments/E003_2/reproduce_injection3_limit.py \
  --out results/E003_2/injection3-limit-reproduction
```
