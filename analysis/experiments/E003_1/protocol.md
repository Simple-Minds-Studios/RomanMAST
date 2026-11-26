# E003.1 Structured Caustic Recovery

Run from the repository's `analysis` directory with bartOS activated. The
archived run used Python 3.12.16, MulensModel 3.12.0, NumPy 2.5.5 and SciPy
1.18.1. Set `MPLBACKEND=Agg` for headless plots.

```sh
cd ~/bartOS-Lab/projects/LensBridge/analysis
python results/E003/verify_archive.py
MPLBACKEND=Agg python structured_recovery.py synthetic --smoke --out results/E003_1-smoke
MPLBACKEND=Agg python structured_recovery.py synthetic --out results/E003_1-synthetic
```

The smoke run only exercises the workflow. For the full run, review every
injection's parameter errors, including the wrapped angle, against the frozen
tolerances. A failed recovery is retained and blocks a global-recovery claim.
The injections cover close, intermediate and wide separation, use the observed
ground-based cadence and simulate independent Gaussian flux noise. They do not
measure recovery under systematics, establish detection completeness or resolve
close/wide degeneracies.

Before accessing independent validation fluxes, freeze and record the holdout
interval, input identity and time provenance, candidate selection, comparison
criteria and stopping rule. The included catalog is pinned by SHA-256 and has
already been analyzed. Its fold 0 and any interval selected retrospectively
from it are development evidence. The following commands use an example
retrospective interval and can run on that catalog.

```sh
MPLBACKEND=Agg python structured_recovery.py fit --holdout 7560.5 7560.9 --out results/E003_1-development
MPLBACKEND=Agg python structured_recovery.py exclude --instrument KMTC --holdout 7560.5 7560.9 --out results/E003_1-exclude-KMTC
```

For genuine confirmation, reserve independently acquired observations and
adapt ingestion to their frozen dataset and cross-calibration before scoring
them. No such observations are supplied. The runner's hash guard intentionally
refuses inputs other than the archived catalog. No published planetary fit was
used to choose bounds, initialization, or injections.

The candidate search uses five mass-ratio bands, three separation bands and
three independent seeds per cell. Separation bands are computational regions.
Candidates are ranked by training loss. The best point candidates from
distinct cells seed uniform-brightness finite-source VBM fits and local
refinement. Single-lens fits and both Gaussian and Student-t runs are fit
independently. Review held-out model scores, per-instrument time and residual
arrays and short-gap adjacent residual correlations. The correlations are
descriptive and do not account for irregular sampling or quantify significance.
Instrument exclusion uses no flux from the excluded instrument to fit physical
parameters. It fits that instrument's flux coefficients with fixed geometry
using only its measurements outside both the holdout and the configured peak
window. All eligible holdout measurements enter scoring.

Annual parallax is a competing single-lens model. Supply sexagesimal ICRS
coordinates and a JSON object containing one full geocentric JD TDB array per
ground instrument, in the source's sorted native-time row order. Verify the
original time scales and reverse any heliocentric correction using the source
provenance before conversion. The archived reduced HJD column alone does not
establish this metadata. Spitzer is outside the analysis. All models in the
comparison use the same converted times and native-time holdout membership.
Record the time conversion and coordinate provenance with the run.

```sh
MPLBACKEND=Agg python structured_recovery.py parallax --holdout 7560.5 7560.9 \
  --test-jd "$E003_JD_TDB_JSON" --coords "$E003_ICRS_COORDS" --out results/E003_1-parallax
```

Repeat the same command and output directory to resume. Each atomic checkpoint
stores the completed batch's population, best candidate and objective history.
Every batch starts a new seeded differential-evolution call, including during
an uninterrupted run. Interruption can require repeating the last incomplete
batch. Optimizer convergence applies to the individual batch and cannot
establish global optimality.
