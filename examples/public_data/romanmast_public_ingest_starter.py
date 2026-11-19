#!/usr/bin/env python3
"""RomanMAST minimal public-data ingestion demonstration (2026-11-19).

Downloads sample observations and preserves their source fields in a CSV.
The default provider samples have separate event identities. The --event-pair
option selects the documented OGLE/KMTNet counterpart pair. The --trifecta
option adds the same event’s published Spitzer photometry.

Not affiliated with NASA, STScI, KASI, OGLE or Spitzer. Read each source's data
policy before use, publication, redistribution, or bulk ingestion.

Usage:
  python romanmast_public_ingest_starter.py --source all
  python romanmast_public_ingest_starter.py --source ogle --output output_demo
  python romanmast_public_ingest_starter.py --event-pair --output same_event_demo
  python romanmast_public_ingest_starter.py --trifecta --output trifecta_demo

The event-pair mode uses the catalog cross-reference linking
KMT-2016-BLG-0113 to OGLE-2016-BLG-1190. It explicitly adds 2450000
to the 2016 KMTNet file's native time column and retains native fields.
HJD's detailed time scale is unspecified in these source files.

Uses only the Python standard library and fetches a bounded set of files.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import tarfile
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = {
    "ogle": {
        "event_id": "OGLE-2026-BLG-0001",
        "url": "https://www.astrouw.edu.pl/ogle/ogle4/ews/2026/blg-0001/phot.dat",
        "cols": ("hjd", "magnitude", "magnitude_error", "seeing_pixels", "sky_level"),
        "notes": "OGLE EWS I-band photometry. Publication usage requires communication with OGLE.",
    },
    "kmtnet": {
        "event_id": "KMT-2025-BLG-0001",
        "url": "https://kmtnet.kasi.re.kr/~ulens/event/2025/data/KB250001/pysis/KMTA01_I.pysis",
        "cols": ("hjd", "delta_flux", "flux_error", "magnitude", "magnitude_error", "fwhm", "sky_level", "airmass"),
        "notes": "KMTNet pySIS I-band. This file is one observatory/reduction, not all event data.",
    },
    "spitzer": {
        "event_id": "OGLE-2015-BLG-0011",
        "url": "https://www.astronomy.ohio-state.edu/Spitzer2015/data/OGLE-2015-BLG-0011/phot_1.dat",
        "cols": ("hjd_minus_2450000", "flux_arbitrary_units", "flux_error_arbitrary_units"),
        "notes": "Spitzer IRAC reduction variant 1; flux in arbitrary units. Other reductions exist.",
    },
}

PAIR_SOURCES = {
    "ogle": {
        **SOURCES["ogle"],
        "event_id": "OGLE-2016-BLG-1190",
        "url": "https://www.astrouw.edu.pl/ogle/ogle4/ews/2016/blg-1190/phot.dat",
        "time_origin": 0.0,
        "canonical_event_id": "OGLE-2016-BLG-1190",
    },
    "kmtnet": {
        **SOURCES["kmtnet"],
        "event_id": "KMT-2016-BLG-0113",
        "url": "https://kmtnet.kasi.re.kr/ulens/event/2016/data/KB160113/pysis/KMTC03_I.pysis",
        "time_origin": 2450000.0,
        "canonical_event_id": "OGLE-2016-BLG-1190",
        "notes": "KMTC03 I-band pySIS. Time offset verified against 2016 event epoch; instrumental flux scale retained.",
    },
}

PAIR_MATCH = {
    "canonical_event_id": "OGLE-2016-BLG-1190",
    "aliases": ["KMT-2016-BLG-0113", "OB161190", "MOA-2016-BLG-383"],
    "evidence_checked_date": "2026-11-19",
    "cross_reference_url": "https://kmtnet.kasi.re.kr/ulens/event/2016/view.php?event=KMT-2016-BLG-0113",
    "ogle_event_url": "https://ogle.astrouw.edu.pl/ogle4/ews/2016/blg-1190.html",
    "coordinate_separation_arcsec": 0.2665794802,
    "ogle_j2000": ["17:58:52.30", "-27:36:48.8"],
    "kmtnet_j2000": ["17:58:52.32", "-27:36:48.82"],
    "event_identity_basis": "Catalog cross-reference OB161190, supported by coordinate proximity",
    "time_convention": "Full HJD after explicit origin offset; detailed time scale unspecified",
    "photometry_status": "Native observatory and reduction scales retained; calibration required for a joint fit",
    "model_metadata": {"ogle_tau_days": 8.021, "kmtnet_t_E_days": 199.96,
                       "status": "Preliminary catalog estimates conflict; preserve provider and model context"},
    "reduction_context": "Ryu et al. report re-reduced OGLE photometry differs from the original online reduction",
    "reference_paper_url": "https://research-repository.st-andrews.ac.uk/bitstream/10023/12621/1/Ryu_2017AJ_SpitzerBulge_AAM.pdf",
}

TRIFECTA_SOURCES = {
    **PAIR_SOURCES,
    "spitzer": {
        "event_id": "OGLE-2016-BLG-1190",
        "canonical_event_id": "OGLE-2016-BLG-1190",
        "url": "https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/data_tarballs/Ryu_et_al_2018_AJ_155_40_data.tar.gz",
        "archive_member": "I_Spitzer_L.dat",
        "cols": ("hjd_minus_2450000", "magnitude", "magnitude_error"),
        "time_origin": 2450000.0,
        "flux_unit": "",
        "photometric_scale": "Published magnitude column; zero point/alignment unspecified in archive member. Not assumed to be native calibrated IRAC magnitudes.",
        "notes": "Ryu et al. 2018 AJ 155 40 published Spitzer L-band subset (14 rows), hosted by KMTNet. Distinct reduction from online survey samples; preserve published values. Cite original paper and contributor acknowledgements.",
    },
}
TRIFECTA_MATCH = {
    **PAIR_MATCH,
    "collection_profile": "trifecta",
    "required_providers": ["ogle", "kmtnet", "spitzer"],
    "spitzer_identity_basis": "KMTNet paper archive explicitly groups KMT-2016-BLG-0113/OGLE-2016-BLG-1190/MOA-2016-BLG-383 and lists Spitzer L photometry",
    "published_archive_page": "https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/Ryu_et_al_2018_AJ_155_40.html",
    "paper_doi": "10.3847/1538-3881/aa9be4",
    "acknowledgements_url": "https://kmtnet.kasi.re.kr/ulens/kmtnet_data_archive/webpages/acknowledgments.html",
    "photometry_status": "Online OGLE/KMTNet samples plus published Spitzer reduction; no cross-calibration or physical fit performed. Published Spitzer magnitude zero point/alignment unspecified in member.",
}


def source_payload(download, source):
    """Read only the configured regular tar member, never extract archive paths."""
    member_name = source.get("archive_member")
    if not member_name:
        return download
    with tarfile.open(fileobj=io.BytesIO(download), mode="r:gz") as archive:
        matches = [m for m in archive.getmembers() if m.name == member_name]
        if len(matches) != 1 or not matches[0].isfile():
            raise ValueError("Archive requires one regular member: " + member_name)
        if matches[0].size > 12 * 1024 * 1024:
            raise ValueError("Selected member exceeds size limit")
        return archive.extractfile(matches[0]).read()


FIELDS = ["provider", "event_id", "canonical_event_id", "hjd", "native_time", "time_origin", "magnitude", "magnitude_error", "flux", "flux_error", "flux_unit", "band", "source_url", "native_fields_json"]


def parse_source(provider, text, sources=None):
    """Parse a provider's original ASCII file; do not cross-calibrate values."""
    data = (SOURCES if sources is None else sources)[provider]
    rows = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cells = stripped.split()
        if len(cells) != len(data["cols"]):
            raise ValueError(f"{provider} line {line_number}: expected {len(data['cols'])} columns; found {len(cells)}")
        values = dict(zip(data["cols"], map(float, cells)))
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError(f"{provider} line {line_number}: non-finite numeric value")
        native_time = values.get("hjd_minus_2450000", values.get("hjd"))
        time_origin = data.get("time_origin", 2450000.0 if provider == "spitzer" else 0.0)
        hjd = native_time + time_origin
        if "canonical_event_id" in data and not 2450000 < hjd < 2460000:
            raise ValueError(f"{provider} line {line_number}: unexpected epoch for the 2016 event")
        rows.append({
            "provider": provider,
            "event_id": data["event_id"],
            "canonical_event_id": data.get("canonical_event_id", data["event_id"]),
            "hjd": f"{hjd:.8f}",
            "native_time": native_time,
            "time_origin": time_origin,
            "magnitude": values.get("magnitude", ""),
            "magnitude_error": values.get("magnitude_error", ""),
            "flux": values.get("flux_arbitrary_units", values.get("delta_flux", "")),
            "flux_error": values.get("flux_error_arbitrary_units", values.get("flux_error", "")),
            "flux_unit": data.get("flux_unit", "arbitrary_units" if provider == "spitzer" else ("difference_flux_instrumental" if provider == "kmtnet" else "")),
            "band": "Spitzer_IRAC_3.6um" if provider == "spitzer" else "I",
            "source_url": data["url"],
            "native_fields_json": json.dumps(values, sort_keys=True),
        })
    if not rows:
        raise ValueError(f"{provider}: no data rows")
    return rows


def fetch_data(provider, sources=None):
    source = (SOURCES if sources is None else sources)[provider]
    req = Request(source["url"], headers={"User-Agent": "RomanMAST-research-demo/0.1 (noncommercial sample retrieval)"})
    with urlopen(req, timeout=30) as response:
        payload = response.read(12 * 1024 * 1024 + 1)
    if len(payload) > 12 * 1024 * 1024:
        raise ValueError(f"{provider}: response larger than demo limit")
    return payload


def run(providers, directory, sources=None):
    sources = SOURCES if sources is None else sources
    directory.mkdir(parents=True, exist_ok=True)
    all_rows, report = [], []
    for provider in providers:
        source = sources[provider]
        print(f"Retrieving {provider}: {source['url']}")
        try:
            download = fetch_data(provider, sources)
            raw = source_payload(download, source)
            rows = parse_source(provider, raw.decode("utf-8"), sources)
            (directory / f"{provider}_source.txt").write_bytes(raw)
            all_rows.extend(rows)
            result = {
                "provider": provider,
                "event_id": source["event_id"],
                "canonical_event_id": source.get("canonical_event_id", source["event_id"]),
                "time_origin": source.get("time_origin", 2450000.0 if provider == "spitzer" else 0.0),
                "url": source["url"],
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "records": len(rows),
                "bytes": len(raw),
                "notes": source["notes"],
                "status": "downloaded_sample_not_scientifically_validated",
                "hjd_range": [min(float(row["hjd"]) for row in rows), max(float(row["hjd"]) for row in rows)],
            }
            if "archive_member" in source:
                (directory / f"{provider}_download.tar.gz").write_bytes(download)
                result.update({"archive_member": source["archive_member"],
                               "download_sha256": hashlib.sha256(download).hexdigest(),
                               "download_bytes": len(download),
                               "photometric_scale": source["photometric_scale"]})
            print(f"  -> {len(rows)} measurements")
        except Exception as err:
            result = {"provider": provider, "url": source["url"], "status": "failed", "error": str(err)}
            print(f"  -> ERROR: {err}")
        report.append(result)
    with (directory / "lightcurve_samples_normalized.csv").open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    (directory / "ingestion_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Completed; output:", directory.resolve())
    if sources is PAIR_SOURCES or sources is TRIFECTA_SOURCES:
        match_spec = TRIFECTA_MATCH if sources is TRIFECTA_SOURCES else PAIR_MATCH
        match = {**match_spec, "download_status": {item["provider"]: item["status"] for item in report}}
        (directory / "event_match.json").write_text(json.dumps(match, indent=2), encoding="utf-8")
        print("Same-event collection uses documented identities. Provider/published photometric scales remain separate.")
    else:
        print("NOTE: samples are unrelated events; no scientific cross-match has been made.")
    return all(item["status"] != "failed" for item in report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["ogle", "kmtnet", "spitzer", "all"], default="ogle")
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--trifecta", action="store_true", help="retrieve OGLE, KMTNet and published Spitzer measurements of OGLE-2016-BLG-1190")
    profile.add_argument("--event-pair", action="store_true", help="retrieve OGLE-2016-BLG-1190 and its documented KMTNet counterpart")
    parser.add_argument("--output", type=Path, default=Path("romanmast_ingest_samples"))
    args = parser.parse_args()
    if args.trifecta:
        success = run(list(TRIFECTA_SOURCES), args.output, TRIFECTA_SOURCES)
    elif args.event_pair:
        success = run(list(PAIR_SOURCES), args.output, PAIR_SOURCES)
    else:
        success = run([args.source] if args.source != "all" else list(SOURCES), args.output)
    raise SystemExit(0 if success else 1)
