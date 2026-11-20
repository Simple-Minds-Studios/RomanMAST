# OGLE-2016-BLG-1093 — second LensBridge example

Verified live retrieval and source reconstruction: 20 November 2026. Canonical event OGLE-2016-BLG-1093; KMTNet counterpart KMT-2016-BLG-1345. MOA alias MOA-2016-BLG-340. The [KMTNet paper index](https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/Shin_et_al_2022_AJ_163_254.html) documents those identities.

This example uses the published figure-data catalog **CDS/VizieR J/AJ/163/254/fig1**, served through the Harvard mirror. It is a single published catalog containing measurements from several observing programs; it is not three new independent archive requests. This differs from the first LensBridge example, which combined online ground-based survey reductions with a published Spitzer subset.

## Completed collection

| Observing program | Instrument | Published measurements selected |
|---|---|---:|
| OGLE | OGLE | 1,368 |
| KMTNet | KMTA (Australia) | 294 |
| KMTNet | KMTC (Chile) | 657 |
| KMTNet | KMTS (South Africa) | 549 |
| Spitzer | IRAC 3.6 μm, catalog L band | 36 |
| **Selected total** | **Three programs, five series** | **2,904** |

The source catalog contains 10,728 rows in total, including **7,824 MOA measurements**. Those remain in the retained catalog snapshot but are explicitly excluded from this three-program CSV. No measurements are invented, resampled, quality-filtered or merged by timestamp. This is a published-data subset, not a claim to collect every exposure of the event.

## Run now

From the repository root, using Python 3.9+ and its standard library:

```sh
python3 examples/public_data/ogle_2016_blg_1093.py --output /tmp/lensbridge-1093
python3 examples/public_data/ogle_2016_blg_1093.py --verify --output /tmp/lensbridge-1093
```

Outputs:

- `catalog_source.tsv`: exact downloaded VizieR response, including catalog, time-origin and column metadata.
- `observations.csv`: selected published magnitudes and uncertainties, full HJD, native reduced HJD, program, instrument, band, original catalog record index and native field values.
- `ingestion_manifest.json`: source URL, actual retrieval timestamp, raw and CSV SHA-256 checksums, source/selected counts and event identity evidence.
- `quality_report.json`: exact reconstruction status, site-specific time ranges, gaps, duplicate epochs and nonpositive-error flags.

For a saved response, use `--input /path/to/catalog_source.tsv`. That path records a local-snapshot processing timestamp instead of inventing a new retrieval time. Network/service availability is required for a fresh download. If the service returns an error page or an unexpected schema, the command exits nonzero; it does not silently reinterpret the response. Provider and normalized measurement files are regenerated locally rather than redistributed in git.

## Explore the light curves

Open [the viewer](../../../examples/public_data/viewer_1093.html) in a browser, then select the generated `observations.csv`. When browsing GitHub source, download the HTML and open it locally, or use the Pages viewer after this change is merged.

The viewer plots OGLE, KMTNet and Spitzer in separate panels on a shared time axis; the three KMTNet sites have distinct colors. It supports an editable time window, a 7550–7570-day window, full-range reset and optional published error bars. Its initial time range preserves the older OGLE baseline. Magnitude increases downward. Each panel has its own vertical scale; no alignment or fitted model is implied. The file stays in the browser and is not uploaded.

## What passed

All 2,904 selected rows reproduce exactly from the saved published catalog bytes. Each observing series is present, with no duplicate epochs or nonpositive errors in this snapshot. A common intersection of all five series' date ranges spans **HJD 2457557.958570–2457594.743440**, or **36.78487 days**. This is a date-range intersection, not continuous or simultaneous coverage.

Eight adapter regression tests cover source/CSV corruption, identity tampering, schema/units errors, overflow, missing Spitzer data, long historical baselines and retained uncertainty flags. The existing 14 tests also pass. The viewer was tested in a browser with the full 2,904-row CSV, time-window changes and error bars. A regression check covers an endpoint-rounding display bug found and fixed during testing.

## Scientific boundary and comparison with the paper

Catalog metadata explicitly defines HJD as **HJD−2450000** and `omag`/`e_omag` as observed magnitudes and magnitude errors, in mag. The script adds 2450000 to the timestamp and preserves the published values. The detailed time scale and cross-instrument magnitude calibration require further review. Source instrument values and reduction provenance remain distinct even when a catalog hosts them together.

Shin et al. 2022 provide observations and modeling context, including the ground/Spitzer color relation and discussion of Spitzer systematics. This run identifies and normalizes that paper's public figure-data release; it does not reproduce the authors' full selection, error renormalization, likelihood or physical solution. No new parallax, mass or discovery is claimed. The next research step is to reconcile each released series with the published modeling inputs and document the needed calibration before any joint fit.

## Credit

- Shin et al. 2022, *OGLE-2016-BLG-1093Lb: A Sub-Jupiter-mass Spitzer Planet Located in the Galactic Bulge*, AJ 163, 254, [DOI 10.3847/1538-3881/ac6513](https://doi.org/10.3847/1538-3881/ac6513).
- [CDS/VizieR catalog](https://cdsarc.cds.unistra.fr/viz-bin/cat/J/AJ/163/254), DOI 10.26093/cds/vizier.51630254; served by the Harvard mirror. Consult the catalog's rights metadata and original contributor acknowledgements when using observations.
- Scientific teams: OGLE, KMTNet, Spitzer and MOA. LensBridge's software license does not relicense their work.
- LensBridge concept originated by Bart Salazar; developed with Brad Devowe / Simple Minds Studios, with AI-assisted implementation and documentation.
