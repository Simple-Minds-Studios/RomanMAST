#!/usr/bin/env python3
"""Verify an ingestion directory against its raw files; report sampling, not calibration."""
import argparse
import csv
import hashlib
import io
import json
import tarfile
from pathlib import Path
from statistics import median
from romanmast_public_ingest_starter import SOURCES, PAIR_SOURCES, PAIR_MATCH, TRIFECTA_SOURCES, TRIFECTA_MATCH, FIELDS, parse_source, source_payload


def validate(directory):
    directory = Path(directory)
    errors, warnings, summaries = [], [], {}
    manifest = json.loads((directory / "ingestion_manifest.json").read_text())
    pair = (directory / "event_match.json").exists()
    match = json.loads((directory / "event_match.json").read_text()) if pair else {}
    triple = match.get("collection_profile") == "trifecta"
    sources = TRIFECTA_SOURCES if triple else (PAIR_SOURCES if pair else SOURCES)
    if pair:
        for key, value in (TRIFECTA_MATCH if triple else PAIR_MATCH).items():
            if match.get(key) != value:
                errors.append(f"event identity metadata differs: {key}")
    with (directory / "lightcurve_samples_normalized.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            errors.append("normalized CSV schema differs")
        actual = list(reader)
    expected = []
    seen = set()
    for item in manifest:
        provider = item.get("provider")
        if provider not in sources or provider in seen:
            errors.append(f"unknown or duplicate provider: {provider}")
            continue
        seen.add(provider)
        if item.get("status") != "downloaded_sample_not_scientifically_validated":
            errors.append(f"source download not successful: {provider}")
            continue
        raw = (directory / f"{provider}_source.txt").read_bytes()
        source = sources[provider]
        if "archive_member" in source:
            download = (directory / f"{provider}_download.tar.gz").read_bytes()
            if source_payload(download, source) != raw:
                errors.append(f"{provider}: extracted member differs from saved source")
            for key, value in {"archive_member": source["archive_member"],
                               "download_sha256": hashlib.sha256(download).hexdigest(),
                               "download_bytes": len(download),
                               "photometric_scale": source["photometric_scale"]}.items():
                if item.get(key) != value:
                    errors.append(f"{provider}: manifest mismatch: {key}")
        rows = parse_source(provider, raw.decode("utf-8"), sources)
        for key, value in {"sha256": hashlib.sha256(raw).hexdigest(),
                           "bytes": len(raw), "records": len(rows),
                           "url": source["url"], "event_id": source["event_id"],
                           "canonical_event_id": source.get("canonical_event_id", source["event_id"]),
                           "time_origin": source.get("time_origin", 2450000.0 if provider == "spitzer" else 0.0)}.items():
            if item.get(key) != value:
                errors.append(f"{provider}: manifest mismatch: {key}")
        times = sorted(float(row["hjd"]) for row in rows)
        bounds = [times[0], times[-1]]
        if item.get("hjd_range") != bounds:
            errors.append(f"{provider}: manifest mismatch: hjd_range")
        gaps = [b-a for a, b in zip(times, times[1:]) if b > a]
        bad_uncertainties = sum(any(row[key] != "" and float(row[key]) <= 0
                                    for key in ("magnitude_error", "flux_error")) for row in rows)
        if bad_uncertainties:
            warnings.append(f"{provider}: {bad_uncertainties} rows have nonpositive uncertainties; retained")
        summaries[provider] = {"records": len(rows), "hjd_range": bounds,
            "duplicate_epochs": len(times)-len(set(times)),
            "median_positive_gap_days": median(gaps) if gaps else None,
            "maximum_gap_days": max(gaps) if gaps else None,
            "nonpositive_uncertainty_rows": bad_uncertainties}
        expected.extend(rows)
    if not seen:
        errors.append("empty source manifest")
    if pair and seen != set(sources):
        errors.append("trifecta is incomplete" if triple else "event pair is incomplete")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(expected)
    buffer.seek(0)
    if actual != list(csv.DictReader(buffer)):
        errors.append("normalized measurements differ from reparsed source bytes")
    overlap = None
    if pair and set(summaries) == set(sources):
        start = max(s["hjd_range"][0] for s in summaries.values())
        end = min(s["hjd_range"][1] for s in summaries.values())
        overlap = {"hjd_start": start, "hjd_end": end,
                   "duration_days": max(0.0, end-start),
                   "has_overlap": start <= end}
    return {"integrity_passed": not errors, "errors": errors, "warnings": warnings,
            "sources": summaries, "overlap": overlap,
            "scope": "Integrity and temporal sampling only; overlapping ranges do not imply continuous or simultaneous coverage. Native scales and unspecified HJD time scales still require scientific review."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.directory)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, tarfile.TarError) as exc:
        report = {"integrity_passed": False, "errors": [str(exc)]}
    output = json.dumps(report, indent=2, allow_nan=False)
    if args.report:
        args.report.write_text(output + "\n")
    print(output)
    raise SystemExit(0 if report["integrity_passed"] else 1)
