#!/usr/bin/env python3
"""Build the compact public demo from a verified four-program 1093 collection."""
import argparse
import csv
import json
from pathlib import Path
from ogle_2016_blg_1093 import validate


def build(directory, output):
    directory, output = Path(directory), Path(output)
    report = validate(directory)
    if not report['integrity_passed'] or report['selected_measurements'] != 10728 or report['provider_counts'].get('moa') != 7824:
        raise ValueError('A verified full four-program 1093 collection is required')
    manifest = json.loads((directory/'ingestion_manifest.json').read_text())
    columns = ['instrument','native_hjd_minus_2450000','magnitude','magnitude_error','source_record']
    with (directory/'observations.csv').open(newline='') as handle:
        rows = [[row[key] for key in columns] for row in csv.DictReader(handle)]
    data = {'schema_version':1,'event_id':'OGLE-2016-BLG-1093',
        'title':'Published 1093 example — four observing programs',
        'paper_doi':'10.3847/1538-3881/ac6513','catalog_doi':'10.26093/cds/vizier.51630254',
        'source_url':manifest['source_url'],'source_sha256':manifest['source_sha256'],
        'normalized_csv_sha256':manifest['normalized_csv_sha256'],
        'retrieved_utc':manifest.get('retrieved_utc'),
        'credit':'Shin et al. 2022, AJ 163, 254; CDS/VizieR; OGLE, KMTNet, Spitzer and MOA teams.',
        'columns':columns,'rows':rows}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False)+'\n')
    return len(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'data/1093.json')
    args=parser.parse_args()
    try:
        print(f'Wrote {build(args.input,args.output)} published demo measurements to {args.output}')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(1,str(exc)+'\n')
