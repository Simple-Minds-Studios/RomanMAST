# RomanMAST — source inventory and proposed ingestion sequence
**Researched:** November 19, 2026 (Eastern)
**Status:** Source inventory and runnable examples added for review. Full live retrieval of the OGLE-2016-BLG-1190 / KMT-2016-BLG-0113 pair was verified on November 19, 2026. Scientific cross-calibration remains pending.

## Why these sources
The RomanMAST `README.md` defines three proposed catalogs: OGLE–Gaia long-event seeds, Spitzer parallax, and OGLE–KMTNet combined light curves. The `datasets/README.md` explicitly calls its current CSVs representative schema templates. The `roadmap.md` lists cross-matching, automated ingestion, and HLSP formatting as future development, not current capabilities.

## Directly documented small test files

| Source | Usable data file | Columns | Caution |
|---|---|---|---|
| OGLE EWS 2026, OGLE-2026-BLG-0001 | https://www.astrouw.edu.pl/ogle/ogle4/ews/2026/blg-0001/phot.dat | HJD, I magnitude, magnitude error, seeing, sky | Public alert photometry; OGLE requires contact for publication use. |
| KMTNet 2025, KMT-2025-BLG-0001, observatory KMTA01 I | https://kmtnet.kasi.re.kr/~ulens/event/2025/data/KB250001/pysis/KMTA01_I.pysis | HJD, difference flux, error, magnitude, error, FWHM, sky, airmass | Only one of many event light-curve files; follow KMTNet's data policy. |
| Spitzer 2015, OGLE-2015-BLG-0011, reduction 1 | https://www.astronomy.ohio-state.edu/Spitzer2015/data/OGLE-2015-BLG-0011/phot_1.dat | HJD-2450000, arbitrary flux, flux error | Different event from the other two samples; flux units are arbitrary. |

**VERY IMPORTANT:** The three sample files are separate astrophysical events, not a scientifically valid joined light curve. To merge data, first establish a documented event-ID crosswalk and time, filter, calibration, and coordinate consistency. OGLE, KMTNet, and Spitzer data have different data policies and measurement systems.

## Archives and programmatic pathways

1. **OGLE alert source and year archives:** https://ogle.astrouw.edu.pl/ogle4/ews/ews.html and https://www.astrouw.edu.pl/ogle/ogle4/ews/2026/ — nightly/current alert event catalogs and individual ASCII `.dat` light curves; publication permission restrictions apply.
2. **KMTNet data:** https://kmtnet.kasi.re.kr/~ulens/ — event and publications archive, with `pySIS` and `DIA` light curves. Seasons up to 2025 listed as public; 2026 listed proprietary as of this check. Search the KMTNet [Data by Event](https://kmtnet.kasi.re.kr/~ulens/kmtnet_data_archive/webpages/DataByEvent.html) cross-ID table before building a real multi-observatory merge.
3. **Gaia DR3:** https://docs.astropy.org/projects/astroquery/en/stable/gaia/gaia.html — TAP/ADQL queries of `gaiadr3.gaia_source` for positions, parallaxes, proper motion, diagnostics. Match carefully in crowded Galactic-bulge fields, with epoch and source-vs-lens ambiguity.
4. **Spitzer 2015 infrared light curves:** https://www.astronomy.ohio-state.edu/Spitzer2015/ — directly accessible `.dat` curves for 170 events, multiple photometry variants; these are photometry files, not already solved parallax-vector measurements.
5. **NASA Exoplanet Archive:** https://exoplanetarchive.ipac.caltech.edu/docs/program_interfaces.html — TAP interface includes a Microlensing `ml` table and confirmed-planet information; useful as reference/validation, not a replacement for raw light curves.
6. **Roman Microlensing Data Challenge 2026 (simulated):** https://rges-pit.org/data-challenge/data/ — Hugging Face `RGES-PIT/Beginner` (~188 events, 9.23 million observations) and `RGES-PIT/Experienced` (2,087 events, 103 million observations), both Parquet. Large; don't download by default. The associated machine-learning observation table is ~172 GB; use selective queries.
7. **OpenUniverse 2024 (simulated Roman/Rubin images):** https://registry.opendata.aws/openuniverse2024/ — `s3://nasa-irsa-simulations/openuniverse2024/roman/preview` and `/full` with anonymous `aws s3 --no-sign-request`. Useful to test Roman-like image/metadata readers but *not* an authentic Roman microlensing stream.
8. **MAST Roman archive and instrument test data:** https://roman-docs.stsci.edu/data-handbook/accessing-wfi-data/the-roman-archive-in-mast and https://archive.stsci.edu/missions-and-data/roman/wfi-triplet-test-data — official public-data plan and detector test files. Some individual detector-test data products are tens of GB: do not bulk-download on a hobby machine.

## Proposed implementation order

1. **Dry-run a single OGLE event.** Store original bytes and SHA256, event ID, retrieval timestamp, source URL and parser version; validate HJD and photometry columns. The attached `romanmast_public_ingest_starter.py` is a limited demo for this stage.
2. **Add one public KMTNet event.** Preserve the observatory, reduction type, filter, measurement/error columns and quality flags. Don't conflate difference flux with calibrated absolute flux.
3. **Use an official event cross-ID.** KMTNet publishes explicit OGLE/KMTNet/MOA name associations. Fetch both providers' measurements for the *same* event. Build shared chronology only after verifying coordinates and timescales.
4. **Query Gaia DR3 around the same event position.** Do not infer that the closest source necessarily represents the lens; crowded-field matching is complex.
5. **Add Spitzer data for a documented overlapping event.** Fit/validate a compatible microlensing model and investigate parallax constraints; having Spitzer photometry alone does not imply parallax has been measured.
6. **Test the schema on a selective RMDC26 simulated sample** (or other Roman simulations), labeling it clearly simulated.
7. **Only after scientific review**, assess HLSP packaging and any proposal to MAST. Maintain copyright, credit, terms and provenance; do not commit large upstream data files to GitHub.

## Python starter
Run locally with Python 3.10+:

```bash
python romanmast_public_ingest_starter.py --source all
```

Creates a separate output folder with three small source files, a manifest, and `lightcurve_samples_normalized.csv`. Each event remains separately identified and is NOT cross-matched. Network access and provider availability are required. The initial parser check used representative rows. The subsequent full live run verified retrieval of 390 OGLE, 1,286 KMTNet and 53 Spitzer rows. The manifest records source byte checksums and time ranges.

## Core source policies
- OGLE EWS https://ogle.astrouw.edu.pl/ogle4/ews/ews.html
- KMTNet https://kmtnet.kasi.re.kr/~ulens/
- Roman MAST https://roman-docs.stsci.edu/data-handbook/accessing-wfi-data/the-roman-archive-in-mast
- OpenUniverse https://registry.opendata.aws/openuniverse2024/
- RMDC26 https://rges-pit.org/data-challenge/data/

The examples now retrieve public historical endpoints. Future Roman flight-data analysis requires separate archive integration.

## Verified same-event ingestion

Run `python3 examples/public_data/romanmast_public_ingest_starter.py --event-pair --output /tmp/romanmast-same-event`. The full live run retrieved 8,801 OGLE rows and 1,745 KMTNet rows. The output CSV contains 10,546 measurements with a shared canonical event ID and separate provider identifiers and photometric scales. KMTNet native HJD-minus-2450000 values receive an explicit offset. Source counts, checksums, retrieval timestamps and time ranges are recorded in [the verification manifest](../examples/public_data/verification_2026-11-19.json).

Catalog cross-reference OB161190 and a coordinate separation of approximately 0.27 arcseconds support the match. Preliminary OGLE and KMTNet duration estimates differ and are retained with provenance. The source reductions and photometric scales require review before a joint physical fit. The default three-unrelated-event mode was also subsequently verified through full live downloads. The 2025 KMTNet sample uses full HJD, consistent with its zero-offset configuration.

## LensBridge three-observatory extension

The [KMTNet paper archive for Ryu et al. 2018](https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/Ryu_et_al_2018_AJ_155_40.html) provides a [509,393-byte tar archive](https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/data_tarballs/Ryu_et_al_2018_AJ_155_40_data.tar.gz) containing `I_Spitzer_L.dat`. Its 14 published time/magnitude/error measurements correspond to the same documented event. The `--trifecta` profile adds that subset to the online pair, for 10,560 rows. The [collection record](../datasets/events/OGLE-2016-BLG-1190/README.md) contains the completed retrieval manifests, quality report, format caveats and contributor acknowledgement links. Published Spitzer magnitude zero point/alignment remains unspecified in the bare member. The full paper archive contains additional data outside this selected demonstration.
