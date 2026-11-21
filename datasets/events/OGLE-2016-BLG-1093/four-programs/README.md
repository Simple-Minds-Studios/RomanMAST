# 1093 with MOA — four observing programs

Verified live retrieval: 20 November 2026. This optional selection retains **all 10,728 rows in the published CDS/VizieR figure-data table** J/AJ/163/254/fig1. It is not a claim to include every exposure of this event or to reproduce the paper's model.

| Program | Published measurements |
|---|---:|
| OGLE | 1,368 |
| KMTNet (KMTA, KMTC, KMTS) | 1,500 |
| Spitzer | 36 |
| MOA | 7,824 |
| **Total** | **10,728** |

## Reproduce

```sh
python3 examples/public_data/ogle_2016_blg_1093.py --include-moa --output /tmp/lensbridge-1093-four-programs
python3 examples/public_data/ogle_2016_blg_1093.py --verify --output /tmp/lensbridge-1093-four-programs
```

Load the resulting `observations.csv` into [the 1093 viewer](../../../../examples/public_data/viewer_1093.html). MOA appears as a fourth, independent R-band panel. Its magnitudes retain their published scale. The three KMTNet instruments remain distinct series in the KMTNet panel. No flux conversion, resampling, photometric alignment or model fit is performed.

The default command still produces the 2,904-row OGLE/KMTNet/Spitzer selection. A manifest records `include_moa` so verification reconstructs the requested selection, rejects selection tampering and continues to recognize older three-program manifests without this field.

The downloaded catalog snapshot contains each original record, column descriptions and time-origin metadata. It receives its own checksum; the normalized CSV receives a separate checksum. Original source-record indices remain available. Data files are regenerated locally, while retrieval and quality records are committed here.

## Validation and limits

All 10,728 normalized observations reproduce exactly from the saved source bytes. The original 2,904-row run also continues to verify. All six instrument series have positive published errors and no duplicate epochs in this snapshot. Their date ranges intersect across 36.78487 days; that is not continuous or simultaneous coverage. Quality fields concern internal consistency, not calibrated uncertainties or absence of systematics. MOA adds historical and high-cadence measurements, but their number alone does not establish a stronger physical constraint.

This is the same published figure-data release used in the [three-program example](../README.md), not a newly independent measurement campaign. Retaining MOA changes the collection's selection and viewer coverage, not the identity of the event or the authorship of the observations.

Credit Shin et al. 2022, AJ 163, 254, DOI 10.3847/1538-3881/ac6513; CDS/VizieR DOI 10.26093/cds/vizier.51630254; and the MOA, OGLE, KMTNet and Spitzer teams. Follow catalog rights and original contributor acknowledgements. LensBridge's software license does not relicense upstream measurements.
