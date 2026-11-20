"""Offline corruption and scientific-quality regression checks."""
import csv
import hashlib
import json
import io
import tarfile
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
from romanmast_public_ingest_starter import PAIR_SOURCES, PAIR_MATCH, TRIFECTA_SOURCES, FIELDS, parse_source, run, source_payload
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


class TrifectaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            data = b"7578.897072 16.475086 0.024981\n7595.076620 17.388009 0.056080\n"
            info = tarfile.TarInfo("I_Spitzer_L.dat")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        self.downloads = {"ogle": b"2457578 17 .1 2 100\n2457596 18 .1 2 100\n",
                          "kmtnet": b"7578 20 1 17 .1 2 100 1.1\n7596 30 1 18 .1 2 100 1.1\n",
                          "spitzer": buffer.getvalue()}
        with patch("romanmast_public_ingest_starter.fetch_data", side_effect=lambda provider, sources: self.downloads[provider]):
            self.assertTrue(run(list(TRIFECTA_SOURCES), self.path, TRIFECTA_SOURCES))

    def test_complete_trifecta(self):
        report = validate(self.path)
        self.assertTrue(report["integrity_passed"])
        self.assertEqual(set(report["sources"]), set(TRIFECTA_SOURCES))
        with (self.path / "lightcurve_samples_normalized.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        spitzer = [row for row in rows if row["provider"] == "spitzer"]
        self.assertEqual(spitzer[0]["hjd"], "2457578.89707200")
        self.assertEqual(spitzer[0]["magnitude"], "16.475086")
        self.assertEqual(spitzer[0]["flux"], "")
        self.assertEqual(spitzer[0]["flux_unit"], "")
        self.assertEqual(len({row["canonical_event_id"] for row in rows}), 1)

    def test_missing_third_source_fails(self):
        path = self.path / "ingestion_manifest.json"
        path.write_text(json.dumps(json.loads(path.read_text())[:2]))
        self.assertIn("trifecta is incomplete", validate(self.path)["errors"])

    def test_container_hash_mismatch_fails(self):
        path = self.path / "ingestion_manifest.json"
        items = json.loads(path.read_text())
        items[-1]["download_sha256"] = "incorrect"
        path.write_text(json.dumps(items))
        self.assertFalse(validate(self.path)["integrity_passed"])

    def test_missing_archive_member_rejected(self):
        with self.assertRaises(ValueError):
            source_payload(self.downloads["spitzer"], {"archive_member": "absent.dat"})

    def test_archive_member_corruption_fails(self):
        path = self.path / "spitzer_source.txt"
        path.write_bytes(path.read_bytes().replace(b"16.475086", b"99.000000"))
        self.assertIn("spitzer: extracted member differs from saved source", validate(self.path)["errors"])

    def test_failed_refresh_cannot_leave_successful_csv(self):
        with patch("romanmast_public_ingest_starter.fetch_data", side_effect=OSError("offline")):
            self.assertFalse(run(list(TRIFECTA_SOURCES), self.path, TRIFECTA_SOURCES))
        with (self.path / "lightcurve_samples_normalized.csv").open() as handle:
            self.assertEqual(list(csv.DictReader(handle)), [])
        self.assertFalse(validate(self.path)["integrity_passed"])


if __name__ == "__main__":
    unittest.main()
