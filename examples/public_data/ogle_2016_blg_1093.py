#!/usr/bin/env python3
"""Retrieve or verify the published OGLE-2016-BLG-1093 three-program example.

Python 3.9+, standard library only. Original catalog bytes remain local.
The downloaded catalog includes MOA, which is retained in source bytes but
excluded from the default OGLE/KMTNet/Spitzer CSV. Use --include-moa
to retain all four published programs (six instrument series).
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CATALOG = "J/AJ/163/254/fig1"
SOURCE_URL = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urlencode({
    "-source": CATALOG, "-out": "Inst,HJD,omag,e_omag,Band", "-out.max": "100000"})
EVENT = "OGLE-2016-BLG-1093"
IDENTITY = {"canonical_event_id": EVENT,
    "aliases": ["KMT-2016-BLG-1345", "MOA-2016-BLG-340"],
    "identity_evidence": "https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/Shin_et_al_2022_AJ_163_254.html",
    "paper_doi": "10.3847/1538-3881/ac6513",
    "catalog_doi": "10.26093/cds/vizier.51630254",
    "time_convention": "Catalog HJD-2450000; add 2450000 for full HJD. Detailed time scale unspecified.",
    "photometry": "Published observed magnitudes and errors; instrument zero points remain separate. No flux conversion, cross-calibration or model fit."}
INSTRUMENTS = {"OGLE": ("ogle", "I"), "KMTA": ("kmtnet", "I"),
               "KMTC": ("kmtnet", "I"), "KMTS": ("kmtnet", "I"),
               "Spitzer": ("spitzer", "L"), "MOA": ("moa", "R")}
SELECTED = {"ogle", "kmtnet", "spitzer"}
FIELDS = ["canonical_event_id", "provider", "instrument", "band", "hjd",
          "native_hjd_minus_2450000", "magnitude", "magnitude_error",
          "source_url", "source_record", "native_fields_json"]


def parse_tsv(payload, include_moa=False):
    if type(include_moa) is not bool:
        raise ValueError("include_moa must be a boolean")
    selected = SELECTED | ({"moa"} if include_moa else set())
    text = payload.decode("utf-8")
    if "#Name: " + CATALOG not in text.splitlines() or "Heliocentric Julian date, HJD-2450000.0" not in text:
        raise ValueError("Missing expected catalog identity or explicit time-origin metadata")
    if any(word in text.lower() for word in ("overflow", "truncated", "#error")):
        raise ValueError("Catalog response reports truncation or an error")
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if len(lines) < 4 or lines[0].split("\t") != ["Inst", "HJD", "omag", "e_omag", "Band"]:
        raise ValueError("Unexpected catalog columns")
    if [c.strip() for c in lines[1].split("\t")] != ["", "d", "mag", "mag", ""]:
        raise ValueError("Unexpected catalog units")
    if not all(cell and set(cell) == {"-"} for cell in lines[2].split("\t")):
        raise ValueError("Missing TSV column separator")
    rows, counts = [], Counter()
    for record, line in enumerate(lines[3:], 1):
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) != 5:
            raise ValueError(f"Record {record}: expected five fields")
        instrument, time, mag, error, band = cells
        if instrument not in INSTRUMENTS:
            raise ValueError(f"Record {record}: unknown instrument {instrument}")
        provider, expected_band = INSTRUMENTS[instrument]
        if band != expected_band:
            raise ValueError(f"Record {record}: unexpected filter {band}")
        t, m, e = map(float, (time, mag, error))
        if not all(map(math.isfinite, (t, m, e))) or not 0 < t < 10000:
            raise ValueError(f"Record {record}: nonfinite values or unexpected reduced HJD epoch")
        counts[instrument] += 1
        if provider in selected:
            rows.append({"canonical_event_id": EVENT, "provider": provider,
                "instrument": instrument, "band": band, "hjd": f"{t+2450000:.8f}",
                "native_hjd_minus_2450000": time, "magnitude": mag,
                "magnitude_error": error, "source_url": SOURCE_URL,
                "source_record": record,
                "native_fields_json": json.dumps(dict(zip(("Inst","HJD","omag","e_omag","Band"), cells)),sort_keys=True)})
    if not counts or sum(counts.values()) >= 100000:
        raise ValueError("Empty catalog or query row limit reached")
    required = set(INSTRUMENTS) if include_moa else set(INSTRUMENTS)-{"MOA"}
    if not required <= set(counts):
        raise ValueError("Selected observation series is missing")
    return rows, dict(counts)


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def quality(rows, counts):
    summaries, warnings = {}, []
    for instrument in sorted({row["instrument"] for row in rows}):
        group = [row for row in rows if row["instrument"] == instrument]
        times = sorted(float(row["hjd"]) for row in group)
        gaps = [b-a for a,b in zip(times,times[1:]) if b>a]
        bad = sum(float(row["magnitude_error"]) <= 0 for row in group)
        if bad:
            warnings.append(f"{instrument}: {bad} nonpositive errors retained")
        summaries[instrument] = {"records": len(group), "hjd_range": [times[0],times[-1]],
            "duplicate_epochs": len(times)-len(set(times)), "nonpositive_error_rows": bad,
            "median_positive_gap_days": median(gaps) if gaps else None,
            "maximum_gap_days": max(gaps) if gaps else None}
    start = max(s["hjd_range"][0] for s in summaries.values())
    end = min(s["hjd_range"][1] for s in summaries.values())
    report = {"selected_measurements": len(rows), "provider_counts": dict(Counter(row["provider"] for row in rows)),
        "source_catalog_instrument_counts": counts, "excluded_MOA_records": counts.get("MOA",0)-sum(row["provider"] == "moa" for row in rows),
        "instruments": summaries, "warnings": warnings,
        "all_selected_series_date_range_intersection": {"start_hjd":start,"end_hjd":end,"days":max(0,end-start),"has_overlap":start<=end},
        "scope": "Published catalog measurements; date-range intersection is not simultaneous/continuous coverage. Magnitude scales and detailed HJD time scales require scientific review; no physical fit."}
    if "MOA" not in summaries:
        report["all_five_series_date_range_intersection"] = report["all_selected_series_date_range_intersection"]
    return report


def validate(directory):
    directory = Path(directory)
    raw = (directory/"catalog_source.tsv").read_bytes()
    manifest = json.loads((directory/"ingestion_manifest.json").read_text())
    rows, counts = parse_tsv(raw, manifest.get("include_moa", False))
    errors = []
    for key,value in {"source_url": SOURCE_URL,"source_sha256":hashlib.sha256(raw).hexdigest(),
        "source_bytes":len(raw),"source_catalog_rows":sum(counts.values()),"selected_rows":len(rows),
        "normalized_csv_sha256":hashlib.sha256(csv_bytes(rows)).hexdigest(),
        "identity":IDENTITY,"source_catalog_instrument_counts":counts}.items():
        if manifest.get(key) != value:
            errors.append("Manifest mismatch: "+key)
    if (directory/"observations.csv").read_bytes() != csv_bytes(rows):
        errors.append("Normalized CSV differs from source reconstruction")
    return {"integrity_passed":not errors,"errors":errors,**quality(rows,counts)}


def collect(directory, input_path=None, include_moa=False):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    if input_path:
        raw = Path(input_path).read_bytes()
        retrieval = {"input_kind":"local_snapshot","input_file":Path(input_path).name,
                     "processed_utc":datetime.now(timezone.utc).isoformat()}
    else:
        request = Request(SOURCE_URL,headers={"User-Agent":"LensBridge/0.2 bounded-public-research-example"})
        with urlopen(request,timeout=30) as response:
            raw = response.read(4000001)
        retrieval = {"input_kind":"live_download","retrieved_utc":datetime.now(timezone.utc).isoformat()}
    if len(raw)>4000000:
        raise ValueError("Catalog exceeds example download limit")
    rows,counts = parse_tsv(raw, include_moa)
    normalized = csv_bytes(rows)
    manifest = {"source_url":SOURCE_URL,"source_sha256":hashlib.sha256(raw).hexdigest(),
        "source_bytes":len(raw),"source_catalog_rows":sum(counts.values()),"selected_rows":len(rows),
        "normalized_csv_sha256":hashlib.sha256(normalized).hexdigest(),"identity":IDENTITY,
        "source_catalog_instrument_counts":counts,"include_moa":include_moa,**retrieval}
    (directory/"catalog_source.tsv").write_bytes(raw)
    (directory/"observations.csv").write_bytes(normalized)
    (directory/"ingestion_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    report = validate(directory)
    (directory/"quality_report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("lensbridge_1093"))
    parser.add_argument("--input",type=Path,help="Parse a saved VizieR response; records processing time, not a new retrieval")
    parser.add_argument("--include-moa",action="store_true",help="include the published MOA R-band series as a fourth program")
    parser.add_argument("--verify",action="store_true",help="Verify an existing output directory without network access")
    args = parser.parse_args()
    try:
        if args.verify and args.include_moa:
            parser.error("--verify reads the saved selection; omit --include-moa")
        report = validate(args.output) if args.verify else collect(args.output,args.input,args.include_moa)
        print(json.dumps(report,indent=2))
        raise SystemExit(0 if report["integrity_passed"] else 1)
    except (OSError,ValueError,KeyError,TypeError,csv.Error) as exc:
        print(json.dumps({"integrity_passed":False,"errors":[str(exc)]},indent=2))
        raise SystemExit(1)
