# RomanMAST public data examples

These Python 3.9+ scripts use the standard library. Run them from this directory or use their full paths. Successful downloads require access to the providers' websites.

## Historical event with an OGLE/KMTNet cross-reference

```sh
python3 romanmast_public_ingest_starter.py --event-pair --output /tmp/romanmast-same-event
```

This selects OGLE-2016-BLG-1190 and KMT-2016-BLG-0113 using the KMTNet catalog's cross-reference OB161190 and supporting coordinates, approximately 0.27 arcseconds apart. The 2016 KMTNet time column is offset by 2450000 to produce full HJD. The detailed source time scale remains unspecified. Each instrument's native fields, event identifier, photometric scale, raw bytes, retrieval time and SHA-256 are retained. Outputs include a source manifest, event identity record and normalized CSV. A nonzero exit status indicates at least one source failed.

The provider catalogs' preliminary duration estimates differ. Preserve both with their reduction and model context. Calibrating the photometry and fitting the event require additional analysis. The corresponding research paper documents differences between original and re-reduced OGLE photometry.

The default `--source all` selects three unrelated example events across OGLE, KMTNet and Spitzer. Each retains a separate canonical event identity. A full live default run retrieved 390 OGLE, 1,286 KMTNet and 53 Spitzer measurements. The 2025 KMTNet sample already contains full HJD, while the 2016 counterpart file uses the explicitly configured offset. The shared chronology example is selected with `--event-pair`.

## OGLE historical brightness check

```sh
python3 ogle_2011_blg_0462.py --csv /tmp/ogle-2011-blg-0462.csv
```

This retrieves OGLE's original I-band photometry for OGLE-2011-BLG-0462 and compares declared reference and near-peak windows. It also accepts `--input /path/to/phot.dat` for an existing download. The reported flux ratio concerns measured blended light. Inferring the lens mass requires additional measurements and an appropriate lensing model.

## Validation and scientific scope

The 2016 pair parser and manifest were checked with 75 actual source rows obtained through web retrieval. The OGLE benchmark was also executed on its full 3,718-row source file and reproduced the 13.91x measured-flux comparison. A full live pair run retrieved 8,801 OGLE and 1,745 KMTNet measurements. Counts, source checksums and time ranges are in [the verification manifest](verification_2026-11-19.json). Published observatory permissions, acknowledgements and data restrictions remain applicable. These files supply ingestion and provenance examples for further scientific review.

Source links and formats are in the [source inventory](../../docs/RomanMAST_data_sources_2026-11-19.md).

The [2016 OGLE event page](https://ogle.astrouw.edu.pl/ogle4/ews/2016/blg-1190.html) and [KMTNet counterpart page](https://kmtnet.kasi.re.kr/ulens/event/2016/view.php?event=KMT-2016-BLG-0113) document the identity used here. [Ryu et al.](https://research-repository.st-andrews.ac.uk/bitstream/10023/12621/1/Ryu_2017AJ_SpitzerBulge_AAM.pdf) describe the scientific analysis and reduction differences.

## Integrity and temporal sampling

After a same-event retrieval, run:

```sh
python3 validate_ingestion.py /tmp/romanmast-same-event --report /tmp/quality.json
python3 -m unittest discover -s . -p test_validation.py
```

The validator reparses saved raw bytes, verifies hashes, lengths, row counts, provider metadata and time ranges, and compares every normalized CSV field with that reconstruction. A mismatch exits nonzero. It also reports duplicate epochs, sampling gaps, nonpositive uncertainties and the intersection of observing date ranges. It never removes flagged measurements or cross-calibrates photometry.

The [saved full-pair report](event_pair_quality_2026-11-19.json) passes integrity for all 10,546 rows. The date-range intersection spans 240.69644 days. OGLE’s median positive gap is about 44.56 minutes and KMTNet’s is 27.89 minutes. These are whole-file sampling summaries; seasonal gaps and irregular sampling remain. The largest gaps are about 104.36 and 8.82 days respectively. Date-range intersection does not establish simultaneous coverage or a scientific match beyond the documented catalog identity.

These checks establish internal consistency with saved provider bytes, not source authenticity, calibrated uncertainties or readiness for joint physical inference. Default unrelated-provider downloads can also be validated; no cross-event overlap is computed.
