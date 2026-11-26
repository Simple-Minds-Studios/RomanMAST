"""Recompute E003 diagnostics from archived standardized residuals."""
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parent
summary = {}
for path in sorted(root.glob("point_fold*.json")):
    if path.stem.endswith("_checkpoint"):
        continue
    report = json.loads(path.read_text())
    single, binary = report["single"], report["binary"]
    by_instrument, observations = {}, []
    for name, b in binary["instruments"].items():
        a = single["instruments"][name]
        assert a["time"] == b["time"] and a["train"] == b["train"]
        contributions = {True: [], False: []}
        for t, za, zb, train in zip(b["time"], a["residual"], b["residual"], b["train"], strict=True):
            delta = za**2 - zb**2
            contributions[train].append(delta)
            if not train:
                observations.append(dict(instrument=name, reduced_hjd=t, single_z=za, binary_z=zb, delta=delta))
        by_instrument[name] = dict(training=math.fsum(contributions[True]), held_out=math.fsum(contributions[False]))
    for key, field in [("training", "delta_train"), ("held_out", "delta_test")]:
        assert math.isclose(sum(v[key] for v in by_instrument.values()), report[field], abs_tol=1e-8)
    for label in ("single", "binary"):
        checkpoint = json.loads((root / f"{path.stem}_{label}_checkpoint.json").read_text())
        assert [row["generation"] for row in checkpoint] == list(range(1, len(checkpoint) + 1))
        assert report[label]["train_chi2"] <= checkpoint[-1]["train_chi2"] + 1e-8
    worst = sorted(observations, key=lambda row: row["delta"])[:10]
    summary[report["seed"]] = dict(delta_train=report["delta_train"], delta_test=report["delta_test"],
                                   binary_converged=binary["success"], instruments=by_instrument, worst=worst)
window = sorted(summary[2027]["worst"][:9], key=lambda row: row["reduced_hjd"])
assert all(row["instrument"] == "KMTC" and row["binary_z"] > row["single_z"] > 0 for row in window)
summary["seed_2027_kmtc_window"] = dict(hours=24*(window[-1]["reduced_hjd"]-window[0]["reduced_hjd"]), observations=window)
print(json.dumps(summary, indent=2, allow_nan=False))
