"""Repeat the archived E003.1 injection-3 local controls at two budgets."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from binary_search import CONFIG, ROOT, atomic, load
from structured_recovery import SETTINGS, evaluate, magnify
from synthetic_validation import Experiment, differences, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(SETTINGS.read_text())
    base = json.loads(CONFIG.read_text())
    catalog = ROOT.parent/"examples/public_data/data/1093.json"
    groups = load(catalog, base)
    control = ROOT/"results/E003_1/evidence/synthetic-controls/run_controls.py"
    tolerances = np.array(cfg["recovery_tolerances"])
    bounds = np.asarray(base["bounds"], dtype=float)
    bounds[3] = cfg["log_q_edges"][0], cfg["log_q_edges"][-1]
    bounds[4] = np.log10([cfg["s_edges"][0], cfg["s_edges"][-1]])
    budgets = [30, 100]
    manifest = dict(configured=dict(injection=3, noise_seed=3329, noise_fraction=.015,
                                    cadence_strides=[1, 30], max_nfev=budgets,
                                    holdout=[7585, 7587], ftol=1e-6, diff_step=1e-4),
                    effective=dict(bounds=bounds.tolist(), runs={}),
                    implementation={p.name: sha(p) for p in
                                    (Path(__file__), control, ROOT/"structured_recovery.py",
                                     ROOT/"binary_search.py", ROOT/"synthetic_validation.py")},
                    sources=dict(catalog_sha256=sha(catalog), frozen_settings_sha256=sha(SETTINGS)))
    for mode, stride in (("historical-full", 1), ("historical-reduced", 30)):
        rng = np.random.default_rng(3329)
        for params in cfg["injections"]:
            truth = np.array(params)
            injected = {}
            for name, group in groups.items():
                t = group[0][::stride]
                flux = 0.6*magnify(truth, "finite", None, t)+0.4
                error = 0.015*flux
                y = flux+rng.normal(scale=error)
                injected[name] = t, y, error, (t < 7585) | (t >= 7587)
        expected_path = control.parent/f"injection-3-{mode}.json"
        expected = json.loads(expected_path.read_text())
        results = []
        for budget in budgets:
            trace = []

            def residual(offset):
                p = truth+tolerances*offset
                detail = evaluate(p, injected, "finite", details=True)
                z = np.concatenate([np.asarray(row["residual"])[row["train"]] for row in detail.values()])
                trace.append(dict(p=p.tolist(), chi2=float(z @ z)))
                return z

            fit = least_squares(residual, np.zeros(7),
                                bounds=((bounds[:, 0]-truth)/tolerances, (bounds[:, 1]-truth)/tolerances),
                                max_nfev=budget, diff_step=1e-4, ftol=1e-6)
            p = truth+tolerances*fit.x
            objective = evaluate(p, injected, "finite")
            errors = differences(p, truth)
            results.append(dict(configured_max_nfev=budget, nfev=fit.nfev, residual_calls=len(trace),
                                status=int(fit.status), converged=bool(fit.success), message=fit.message,
                                p=p.tolist(), objective=objective, optimality=float(fit.optimality),
                                active_bounds=fit.active_mask.tolist(), errors=errors.tolist(),
                                frozen_pass=bool(np.all(errors <= tolerances)), history=trace))
        exact_budget = results[0]
        expected_fit = expected["local"]
        data = Experiment(injected).identity()
        report = dict(mode=mode, dataset=data, truth=truth.tolist(), results=results,
                      archived_report_sha256=sha(expected_path),
                      objective_reproduced=bool(np.isclose(expected_fit["objective"], exact_budget["objective"],
                                                          atol=1e-8, rtol=1e-10)),
                      termination_reproduced=(expected_fit["success"], expected_fit["nfev"]) ==
                                             (exact_budget["converged"], exact_budget["nfev"]))
        manifest["effective"]["runs"][mode] = dict(dataset=data, evaluations=[r["nfev"] for r in results])
        atomic(args.out/f"{mode}.json", report)
        print(mode, [(r["nfev"], r["status"], r["objective"], r["frozen_pass"]) for r in results], flush=True)
    atomic(args.out/"manifest.json", manifest)


if __name__ == "__main__":
    main()
