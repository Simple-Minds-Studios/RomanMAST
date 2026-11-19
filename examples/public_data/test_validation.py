"""Offline corruption and scientific-quality regression checks."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from romanmast_public_ingest_starter import PAIR_SOURCES, PAIR_MATCH, FIELDS, parse_source
from validate_ingestion import validate


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        raws = {"ogle": b"2457500 17 .1 2 100\n2457501 16 .1 2 100\n",
                "kmtnet": b"7500 20 1 17 .1 2 100 1.1\n7501 30 1 16 .1 2 100 1.1\n"}
        all_rows, manifest = [], []
        for provider, raw in raws.items():
            source = PAIR_SOURCES[provider]
            rows = parse_source(provider, raw.decode(), PAIR_SOURCES)
            all_rows.extend(rows)
            (self.path / f"{provider}_source.txt").write_bytes(raw)
            manifest.append({"provider": provider, "status": "downloaded_sample_not_scientifically_validated",
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "records": len(rows),
                "url": source["url"], "event_id": source["event_id"],
                "canonical_event_id": source["canonical_event_id"], "time_origin": source["time_origin"],
                "hjd_range": [2457500.0, 2457501.0]})
        (self.path / "ingestion_manifest.json").write_text(json.dumps(manifest))
        (self.path / "event_match.json").write_text(json.dumps(PAIR_MATCH))
        with (self.path / "lightcurve_samples_normalized.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

    def test_valid_pair(self):
        report = validate(self.path)
        self.assertTrue(report["integrity_passed"])
        self.assertEqual(report["overlap"]["duration_days"], 1)

    def test_corrupted_raw(self):
        path = self.path / "ogle_source.txt"
        path.write_bytes(path.read_bytes().replace(b"17", b"18"))
        report = validate(self.path)
        self.assertFalse(report["integrity_passed"])
        self.assertIn("ogle: manifest mismatch: sha256", report["errors"])

    def test_csv_time_origin_tampering(self):
        path = self.path / "lightcurve_samples_normalized.csv"
        path.write_text(path.read_text().replace("2457500.00000000", "7500.00000000"))
        self.assertFalse(validate(self.path)["integrity_passed"])

    def test_missing_pair_provider(self):
        path = self.path / "ingestion_manifest.json"
        path.write_text(json.dumps(json.loads(path.read_text())[:1]))
        self.assertIn("event pair is incomplete", validate(self.path)["errors"])

    def test_unrecognized_download_status(self):
        path = self.path / "ingestion_manifest.json"
        items = json.loads(path.read_text())
        items[0]["status"] = "invented_status"
        path.write_text(json.dumps(items))
        self.assertFalse(validate(self.path)["integrity_passed"])

    def test_identity_metadata_tampering(self):
        path = self.path / "event_match.json"
        match = json.loads(path.read_text())
        match["canonical_event_id"] = "unrelated event"
        path.write_text(json.dumps(match))
        self.assertFalse(validate(self.path)["integrity_passed"])

    def test_nonfinite_source_rejected(self):
        with self.assertRaises(ValueError):
            parse_source("ogle", "2457500 nan .1 2 100", PAIR_SOURCES)

    def test_bad_error_retained_for_quality_report(self):
        rows = parse_source("ogle", "2457500 17 -1 2 100", PAIR_SOURCES)
        self.assertEqual(rows[0]["magnitude_error"], -1)


if __name__ == "__main__":
    unittest.main()
