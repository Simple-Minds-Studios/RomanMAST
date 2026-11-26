# E001 — Incremental Observatory Contribution

Positive control: OGLE-2016-BLG-1093 (Shin et al. 2022, DOI 10.3847/1538-3881/ac6513; catalog DOI 10.26093/cds/vizier.51630254).

1. Verify original catalog bytes and normalized CSV using existing ingestion code. Reject missing records, nonfinite values, nonpositive errors and unexplained duplicates.
2. Preserve reduced HJD convention; review time scales before parallax fitting. Convert magnitudes to relative flux independently per instrument; propagate errors and retain source/blend nuisance parameters.
3. Validate point-lens implementation with seeded synthetic controls before fitting real observations. Record optimizer starts, bounds, convergence, residuals and versions.
4. Fit A (OGLE), B (+KMTNet), C (+MOA). Compare on common held-out time blocks with identical scoring; do not compare raw chi-square across unequal datasets.
5. Fit competing binary-lens solutions with finite-source effects where required. Explore degeneracies and correlated noise; report uncertainty and failures.
6. D adds Spitzer only with validated observer ephemerides and parallax geometry. E adds explicitly simulated Roman astrometry, never represented as observed data.
7. Compare physical parameters and uncertainty with published benchmark; document discrepancies rather than tune to agreement. No candidate screening until independent review.

PDF-derived observations are secondary recovery data, not checksum-verified original catalog bytes.
