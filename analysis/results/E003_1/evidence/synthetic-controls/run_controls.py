import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from structured_recovery import CONFIG, SETTINGS, ROOT, evaluate, load, magnify

out = Path(sys.argv[1])
base = json.loads(CONFIG.read_text())
cfg = json.loads(SETTINGS.read_text())
groups = load(ROOT.parent/"examples/public_data/data/1093.json", base)
full_times = {name: group[0] for name, group in groups.items()}
tolerances = np.array(cfg["recovery_tolerances"])
rngs = {kind: np.random.default_rng(3329) for kind in ("historical-full", "historical-reduced")}
bounds = np.array(base["bounds"], dtype=float)
bounds[3] = [cfg["log_q_edges"][0], cfg["log_q_edges"][-1]]
bounds[4] = np.log10([cfg["s_edges"][0], cfg["s_edges"][-1]])


def residual(p, groups):
    details = evaluate(p, groups, "finite", details=True)
    return np.concatenate([np.asarray(row["residual"])[row["train"]] for row in details.values()])


def summarize(p, groups):
    details = evaluate(p, groups, "finite", details=True)
    return {name: dict(training_n=sum(row["train"]), held_out_n=row["train"].count(False),
                       training_chi2=row["train_loss"],
                       held_out_chi2=row["test_loss"] if not all(row["train"]) else None,
                       flux=row["flux"]) for name, row in details.items()}


for index, params in enumerate(cfg["injections"], 1):
    truth = np.array(params)
    center = truth[0]
    dense = np.unique(np.concatenate([np.linspace(center-90, center+90, 901),
                                      np.linspace(center-3, center+3, 2401)]))
    scenarios = {
        "historical-full": full_times,
        "historical-reduced": {name: t[::30] for name, t in full_times.items()},
        "dense-noiseless": {"synthetic": dense},
    }
    for mode, times in scenarios.items():
        injected = {}
        for name, t in times.items():
            flux = 0.6*magnify(truth, "finite", None, t)+0.4
            error = 0.015*flux
            observed = flux if mode == "dense-noiseless" else flux+rngs[mode].normal(scale=error)
            train = (t < 7585) | (t >= 7587)
            injected[name] = t, observed, error, train
        at_truth = evaluate(truth, injected, "finite")
        truth_details = summarize(truth, injected)
        report = dict(injection=index, scenario=mode, truth=truth.tolist(), truth_training_chi2=at_truth,
                      truth_by_instrument=truth_details, parameter_tolerances=tolerances.tolist())
        target = out/f"injection-{index}-{mode}.json"
        target.write_text(json.dumps(report, indent=2)+"\n")
        print(index, mode, "truth", at_truth, flush=True)
        try:
            def scaled_residual(offset):
                return residual(truth+tolerances*offset, injected)

            result = least_squares(scaled_residual, np.zeros(7),
                                   bounds=((bounds[:,0]-truth)/tolerances, (bounds[:,1]-truth)/tolerances),
                                   max_nfev=30, diff_step=1e-4, ftol=1e-6)
            p = truth+tolerances*result.x
            errors = abs(p-truth)
            errors[5] = abs((p[5]-truth[5]+180)%360-180)
            report.update(local=dict(parameters=p.tolist(), errors=errors.tolist(),
                                     within_tolerances=bool(np.all(errors <= tolerances)),
                                     objective=evaluate(p, injected, "finite"),
                                     success=bool(result.success), message=result.message,
                                     nfev=result.nfev, by_instrument=summarize(p, injected)))
        except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError) as exc:
            report.update(local=dict(success=False, error=str(exc)))
        target.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
        print(index, mode, "local", report["local"].get("objective"), flush=True)
