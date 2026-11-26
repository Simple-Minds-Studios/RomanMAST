"""Run from analysis/: python run_baseline.py ../examples/public_data/data/1093.json"""
import argparse, hashlib, json, platform
from pathlib import Path
from collections import Counter
import numpy as np
import scipy
from lensbridge.point_lens import prepare, fit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,default=Path("results/E001_baseline.json"))
    args=p.parse_args()
    raw=args.input.read_bytes()
    data=json.loads(raw)
    cfg=json.loads((Path(__file__).parent/"experiments/E001/config.json").read_text())
    rows=data["rows"]
    if data["event_id"]!=cfg["event"] or data["columns"]!=["instrument","native_hjd_minus_2450000","magnitude","magnitude_error","source_record"]:
        raise ValueError("Unexpected event or schema")
    if Counter(r[0] for r in rows)!=cfg["expected_counts"] or len({int(r[4]) for r in rows})!=len(rows) or len({(r[0],float(r[1])) for r in rows})!=len(rows):
        raise ValueError("Record validation failed")
    groups=prepare(rows)
    results={k:fit({n:groups[n] for n in names},7560) for k,names in cfg["runs"].items() if k in ("A","B","C")}
    report={"input_sha256":hashlib.sha256(raw).hexdigest(),"event":cfg["event"],"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"results":results,"limitations":"Input hash identifies supplied JSON, not original catalog. Exploratory fits only; no uncertainty, held-out comparison, binary lens or parallax. Nonnegative blend constraint may bias estimates."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
