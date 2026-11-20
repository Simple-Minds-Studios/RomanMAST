# OGLE-2016-BLG-1190 — three-observatory collection

Verified full retrieval: 19 November 2026. Canonical event OGLE-2016-BLG-1190, counterpart KMT-2016-BLG-0113.

| Measurements | Selected source/reduction | Count |
|---|---|---:|
| OGLE | Original online EWS I-band file | 8,801 |
| KMTNet | KMTC03 I-band online pySIS file | 1,745 |
| Spitzer | Ryu et al. 2018 paper archive, `I_Spitzer_L.dat` | 14 |
| Total | Three selected measurement sets | 10,560 |

This completes the selected three-provider demonstration, not the full observational inventory of the event. The published archive also includes other telescopes, KMTNet sites/fields and re-reduced ground photometry, which are not ingested by this profile. No measurements are synthesized, resampled, merged by timestamp or cross-calibrated.

## Reproduce the measurement collection

From the repository root, with Python 3.9+ and network access:

```sh
python3 examples/public_data/romanmast_public_ingest_starter.py --trifecta --output /tmp/lensbridge-trifecta
python3 examples/public_data/validate_ingestion.py /tmp/lensbridge-trifecta --report /tmp/lensbridge-trifecta/quality_report.json
```

The resulting directory contains the original OGLE/KMTNet source bytes, original published Spitzer member, its downloaded tar archive, all 10,560 normalized CSV rows, and identity/provenance records. The source measurements are retrieved from their providers rather than redistributed in git. The committed manifests and quality report document the completed run and let readers compare hashes and row counts; provider files may change later.

## Identity, time and photometric scales

The [paper archive page](https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/Ryu_et_al_2018_AJ_155_40.html) explicitly associates all three event aliases and lists Spitzer L photometry. The downloaded member contains 14 three-column rows, consistent with the analyzed Spitzer count in Table 1 of [Ryu et al. 2018](https://doi.org/10.3847/1538-3881/aa9be4). This is the paper's published subset, not all Spitzer exposures.

The Spitzer columns are time, published magnitude and magnitude error. Add 2450000 to its reduced HJD time, as for the selected 2016 KMTNet file. Full HJD is a common origin convention; the detailed time scales remain unspecified. The member has no column header or zero-point metadata. Preserve its published magnitude column without claiming native calibrated IRAC magnitudes or inferring flux. The paper discusses model-based alignment for its plotted curves; it does not establish from the bare member alone which alignment the released values use. A quantitative comparison needs that clarification.

OGLE/KMTNet online survey reductions differ from the paper's re-reduced ground measurements. The original catalog duration discrepancy is retained. Combining records under one event ID is a collection operation, not a reproduction of the paper's fit.

## Validation

The validator reconstructs every normalized CSV field from saved source bytes and verifies hashes, counts, lengths, metadata and epochs. For Spitzer it also verifies the downloaded archive hash and that the single selected regular member matches the saved source bytes. It never extracts archive paths to disk.

All 10,560 rows pass integrity. Their date ranges intersect from HJD 2457578.897072 to 2457595.076620: 16.179548 days. This describes date ranges, not simultaneous or continuous sampling. The Spitzer subset has a median positive gap of approximately 1.254 days. No duplicate epochs or nonpositive uncertainties occur in these selected files; that does not establish calibrated error bars or absence of systematics.

## Credit and use

Observations and published reductions belong to the contributing scientific teams. Cite Ryu et al. 2018, AJ 155, 40, DOI 10.3847/1538-3881/aa9be4 and follow the [archive contributor acknowledgements](https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/acknowledgments.html), including Spitzer, OGLE and KMTNet as relevant. OGLE online EWS publication-use requirements remain applicable. LensBridge's software license does not relicense upstream observations.

LensBridge project concept: Bart Salazar. Development with Brad Devowe / Simple Minds Studios. AI-assisted implementation and documentation, with recorded validation and scientific limitations. No new discovery, fitted parallax or lens mass is claimed.
