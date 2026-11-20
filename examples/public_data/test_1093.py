"""Offline regression tests for the published 1093 catalog adapter."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from ogle_2016_blg_1093 import CATALOG, collect, parse_tsv, validate

FIXTURE = ("#Name: "+CATALOG+"\n#Column HJD Heliocentric Julian date, HJD-2450000.0\n"
    "Inst\tHJD\tomag\te_omag\tBand\n \td\tmag\tmag\t\n-------\t-----------\t---------\t---------\t-\n"
    "KMTA\t7559\t18.0\t0.1\tI\nKMTC\t7560\t17.0\t0.1\tI\nKMTS\t7561\t18.0\t0.1\tI\n"
    "MOA\t7560\t16.0\t0.1\tR\nOGLE\t5260\t20.0\t0.1\tI\nOGLE\t7560\t17.0\t0.1\tI\n"
    "Spitzer\t7558\t16.0\t0.1\tL\nSpitzer\t7594\t16.5\t0.1\tL\n")


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.input = self.path/'input.tsv'
        self.input.write_text(FIXTURE)
        self.output = self.path/'output'

    def test_collection_roundtrip_and_exclusion(self):
        report = collect(self.output,self.input)
        self.assertTrue(report['integrity_passed'])
        self.assertEqual(report['selected_measurements'],7)
        self.assertEqual(report['excluded_MOA_records'],1)
        self.assertEqual(report['provider_counts'],{'kmtnet':3,'ogle':2,'spitzer':2})
        manifest = json.loads((self.output/'ingestion_manifest.json').read_text())
        self.assertEqual(manifest['input_kind'],'local_snapshot')
        self.assertNotIn('retrieved_utc',manifest)
        with (self.output/'observations.csv').open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(rows[3]['hjd'],'2455260.00000000')
        self.assertEqual(rows[3]['source_record'],'5')
        self.assertEqual(rows[3]['canonical_event_id'],'OGLE-2016-BLG-1093')
        self.assertEqual(report['all_five_series_date_range_intersection']['has_overlap'],False)

    def test_missing_spitzer_rejected(self):
        with self.assertRaises(ValueError):
            parse_tsv('\n'.join(l for l in FIXTURE.splitlines() if not l.startswith('Spitzer')).encode())

    def test_bad_metadata_rejected(self):
        for payload in (FIXTURE.replace(CATALOG,'wrong/catalog'),FIXTURE.replace('HJD-2450000.0','BJD'),FIXTURE+'\n#INFO OVERFLOW'):
            with self.assertRaises(ValueError):parse_tsv(payload.encode())

    def test_bad_schema_units_filter_and_values(self):
        for payload in (FIXTURE.replace('Inst\tHJD','Inst\tBJD'),FIXTURE.replace(' \td\tmag',' \ts\tmag'),
                        FIXTURE.replace('KMTC','unknown'),FIXTURE.replace('7560\t17.0','nan\t17.0'),
                        FIXTURE.replace('7559\t18.0\t0.1\tI','7559\t18.0\t0.1\tL')):
            with self.assertRaises(ValueError):parse_tsv(payload.encode())

    def test_source_corruption_detected(self):
        collect(self.output,self.input)
        p=self.output/'catalog_source.tsv';p.write_text(p.read_text().replace('18.0','19.0'))
        self.assertFalse(validate(self.output)['integrity_passed'])

    def test_csv_corruption_detected(self):
        collect(self.output,self.input)
        p=self.output/'observations.csv';p.write_text(p.read_text().replace('2455260.00000000','5260.00000000'))
        self.assertFalse(validate(self.output)['integrity_passed'])

    def test_identity_tampering_detected(self):
        collect(self.output,self.input)
        p=self.output/'ingestion_manifest.json';manifest=json.loads(p.read_text())
        manifest['identity']['canonical_event_id']='OGLE-2016-BLG-1190'
        p.write_text(json.dumps(manifest))
        self.assertFalse(validate(self.output)['integrity_passed'])

    def test_nonpositive_uncertainty_retained_and_flagged(self):
        self.input.write_text(FIXTURE.replace('7559\t18.0\t0.1','7559\t18.0\t-0.1'))
        report=collect(self.output,self.input)
        self.assertTrue(report['integrity_passed'])
        self.assertEqual(report['instruments']['KMTA']['nonpositive_error_rows'],1)
        self.assertEqual(report['selected_measurements'],7)


if __name__=='__main__': unittest.main()
