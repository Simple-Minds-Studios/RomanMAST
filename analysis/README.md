# LensBridge scientific analysis

Experiment E001: incremental observatory contribution for OGLE-2016-BLG-1093. This development branch is research infrastructure, not a discovery claim.

Reuse the existing ingestion and validation scripts in examples/public_data. Run `python examples/public_data/ogle_2016_blg_1093.py --include-moa --output lensbridge_1093` and then repeat with `--verify` (omit --include-moa). Preserve source checksums and instrument-specific photometric scales. See experiments/E001/protocol.md.

Status: protocol and configuration established; numerical implementation and independent validation pending. Prior exploratory fits are not certified results.
