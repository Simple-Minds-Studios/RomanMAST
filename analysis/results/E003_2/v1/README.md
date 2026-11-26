# E003.2-v1 synthetic benchmark results

The three injected dense objectives were consistent with zero at truth.
All 12 blind runs missed at least one frozen E003.1 tolerance. The 20-generation
budget improved the dense training score in all six seed/injection comparisons
against the 5-generation budget. The same-seed prefixes overlap in the
convergence plots. The best dense training χ² by injection was 135.52, 11205.64
and 194.85. Effective objective-call counts were 168 and 588.

The paired full cadence had 10,661 training and 31 held-out observations per
injection. Its every-30th-row subset had 358 training and zero held-out
observations. The injection 1 full-cadence source-radius profile varied by
less than 0.03 in χ² across its first four sampled points. Injection 2 had a
much sharper sampled minimum. Local correlation matrices and singular values
are included with each fit. For example, the injection 1 reduced fit had
absolute angle–log-separation correlation of about 0.997, with a local
evaluation-limit flag. Treat this as a local diagnostic.

The opposite close/wide branch was waveform-equivalent under the provisional
0.05-error-unit RMS screen for injections 1 and 3. Their alternate holdout
RMS values were 0.00389 and 0.000312. Injection 2's tested alternate scored
5.32 error units RMS on holdout. These conditional fits neither establish
global uniqueness nor alter the blind parameter-recovery counts.

The legacy injection 3 replay reproduced both 30-evaluation budget-limit
terminations. The final objectives differed from the earlier archive by
about 0.020 in full cadence and 0.0023 in reduced cadence. With a cap of 100,
both fits terminated by the optimizer's relative-cost criterion after 35
evaluations, and both missed the frozen tolerances. The matched-noise
E003.2 control used a different evaluation path and found a tolerance-passing
full-cadence solution with the larger cap, despite a higher training χ² than
its shorter fit. These outcomes expose sensitivity to competing local
solutions and stopping behavior.

No single-lens null triggered the provisional screen in six realizations.
The exact two-sided 95% binomial interval is 0–45.9% for this one geometry
and fitting policy. The largest training improvement was 5.83, below the
pilot cutoff of 25. The null sample is too small to calibrate a detection rule.

The manifest and per-run records retain datasets, hashes, effective settings,
model scores and optimizer traces. E003.2-v1 does not pass a blind-recovery
gate for historical fitting.
