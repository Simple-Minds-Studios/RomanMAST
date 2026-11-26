"""Synthetic-only identifiability and blind recovery controls for E003.2."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import MulensModel as mm
import numpy as np
import scipy
from scipy.optimize import differential_evolution, least_squares, nnls
from scipy.stats import binomtest

from binary_search import CONFIG, ROOT, atomic, load
from structured_recovery import SETTINGS, magnify

CONFIG_2 = ROOT / "experiments/E003_2/config.json"
PARAMETERS = ("t0", "u0", "t_E", "log_q", "log_s", "alpha", "log_rho")
PENALTY = 1e30


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Experiment:
    def __init__(self, groups):
        self.groups = groups
        self.time = np.concatenate([group[0] for group in groups.values()])
        self.train = np.concatenate([group[3] for group in groups.values()])
        self.slices = np.split(np.arange(len(self.time)), np.cumsum(
            [len(group[0]) for group in list(groups.values())[:-1]]))
        self.hash = hashlib.sha256()
        for name, group in groups.items():
            self.hash.update(name.encode() + b"\0")
            for array in group:
                self.hash.update(len(array).to_bytes(8, "little"))
                self.hash.update(np.asarray(array, dtype="<f8").tobytes())

    def residual(self, p, kind, include_holdout=False):
        active = np.ones_like(self.train) if include_holdout else self.train
        amplification = np.empty(len(active))
        amplification[active] = magnify(p, kind, None, self.time[active])
        residual = np.empty(len(active))
        for rows, (_, y, e, train) in zip(self.slices, self.groups.values(), strict=True):
            a = amplification[rows[active[rows]]]
            x = np.column_stack((a, np.ones(len(a)))) / e[active[rows], None]
            target = y[active[rows]] / e[active[rows]]
            fit = train if include_holdout else slice(None)
            coeff = nnls(x[fit], target[fit])[0]
            residual[rows[active[rows]]] = target - x @ coeff
        return residual[active]

    def evaluate(self, p, kind):
        z = self.residual(p, kind, include_holdout=True)
        return dict(training_chi2=float(np.sum(z[self.train]**2)),
                    holdout_chi2=float(np.sum(z[~self.train]**2)) if (~self.train).any() else None)

    def objective(self, p, kind):
        try:
            z = self.residual(p, kind)
            return float(z @ z)
        except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError):
            return PENALTY

    def identity(self):
        return dict(sha256=self.hash.hexdigest(), training_n=int(self.train.sum()),
                    holdout_n=int((~self.train).sum()),
                    per_instrument={key: dict(n=len(v[0]), training_n=int(v[3].sum()))
                                    for key, v in self.groups.items()})


def simulate(times, masks, p, kind, cfg, rng=None):
    groups = {}
    for name, t in times.items():
        f = cfg["source_flux"] * magnify(p, kind, None, t) + cfg["blend_flux"]
        e = cfg["noise_fraction"] * f
        observed = f if rng is None else f + rng.normal(scale=e)
        groups[name] = t, observed, e, masks[name]
    return Experiment(groups)


def reduce(full, stride):
    return Experiment({key: tuple(array[::stride] for array in group)
                       for key, group in full.groups.items()})


def differences(p, truth):
    diff = abs(np.asarray(p) - truth)
    diff[5] = abs((p[5] - truth[5] + 180) % 360 - 180)
    return diff


def blind(data, kind, bounds, seed, generations, multiplier):
    history = []
    start = time.monotonic()

    def callback(intermediate_result):
        history.append(dict(generation=intermediate_result.nit, nfev=intermediate_result.nfev,
                            chi2=float(intermediate_result.fun), p=intermediate_result.x.tolist()))

    result = differential_evolution(lambda p: data.objective(p, kind), bounds,
                                    rng=np.random.default_rng(seed), maxiter=generations,
                                    popsize=multiplier, callback=callback, polish=False, tol=0, atol=0)
    valid = bool(np.isfinite(result.fun) and result.fun < PENALTY)
    return dict(configured=dict(seed=seed, generations=generations, population_multiplier=multiplier,
                                bounds=np.asarray(bounds).tolist(), initialization="latinhypercube"),
                effective=dict(generations=result.nit, population_size=len(result.population),
                               nfev=result.nfev, elapsed_seconds=time.monotonic()-start),
                p=result.x.tolist(), scores=data.evaluate(result.x, kind) if valid else None,
                valid=valid, converged=bool(result.success), message=str(result.message), history=history)


def local(data, initial, bounds, scales, budget, fixed=None):
    initial = np.asarray(initial).copy()
    free = np.arange(len(initial))
    if fixed is not None:
        index, value = fixed
        initial[index] = value
        free = free[free != index]
    low, high = ((bounds[:, i]-initial)/scales for i in range(2))
    trace = []
    start = time.monotonic()

    def residual(offset):
        p = initial.copy()
        p[free] += scales[free]*offset
        z = data.residual(p, "finite")
        trace.append(dict(p=p.tolist(), chi2=float(z @ z)))
        return z

    try:
        fit = least_squares(residual, np.clip(np.zeros(len(free)), low[free], high[free]),
                            bounds=(low[free], high[free]), max_nfev=budget,
                            diff_step=1e-4, ftol=1e-6)
        p = initial.copy()
        p[free] += scales[free]*fit.x
        singular = np.linalg.svd(fit.jac, compute_uv=False)
        covariance = np.linalg.pinv(fit.jac.T @ fit.jac, hermitian=True)
        sigma = np.sqrt(np.maximum(covariance.diagonal(), 0))
        denominator = np.outer(sigma, sigma)
        correlation = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator>0)
        return dict(p=p.tolist(), valid=True, scores=data.evaluate(p, "finite"),
                    message=fit.message, converged=bool(fit.success), status=int(fit.status),
                    optimality=float(fit.optimality), active_bounds=fit.active_mask.tolist(),
                    free_parameters=[PARAMETERS[i] for i in free], singular_values=singular.tolist(),
                    correlation=correlation.tolist(), nfev=fit.nfev, residual_calls=len(trace),
                    configured_max_nfev=budget, elapsed_seconds=time.monotonic()-start, history=trace)
    except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError) as exc:
        return dict(valid=False, message=str(exc), configured_max_nfev=budget,
                    elapsed_seconds=time.monotonic()-start, residual_calls=len(trace), history=trace)


def annotate(result, truth, scales):
    if result["valid"]:
        errors = differences(result["p"], truth)
        result.update(parameter_errors=errors.tolist(), frozen_pass=bool(np.all(errors <= scales)))
    return result


def profile(data, truth, bounds, scales, cfg, alternate):
    profiles = {}
    for index in (6, 3, 4, 2):
        grid = np.unique(np.clip(truth[index] + scales[index]*np.asarray(cfg["profile_offsets_in_tolerances"]),
                                 *bounds[index]))
        rows = []
        for value in grid:
            runs = [local(data, start, bounds, scales, cfg["profile_local_evaluations"], (index, value))
                    for start in (truth, alternate)]
            valid = [run for run in runs if run["valid"]]
            rows.append(dict(value=float(value), runs=runs,
                             best_chi2=min((run["scores"]["training_chi2"] for run in valid), default=None)))
        profiles[PARAMETERS[index]] = rows
    return profiles


def geometry_comparison(data, truth, candidates, cfg):
    z = data.residual(truth, "finite", include_holdout=True)
    for label, result in candidates.items():
        if not result["valid"]:
            continue
        prediction_difference = z - data.residual(result["p"], "finite", include_holdout=True)
        train = float(np.sqrt(np.mean(prediction_difference[data.train]**2)))
        holdout = float(np.sqrt(np.mean(prediction_difference[~data.train]**2)))
        result.update(region=label, training_prediction_rms_sigma=train, holdout_prediction_rms_sigma=holdout,
                      waveform_equivalent=bool(max(train, holdout) <= cfg["predictive_equivalence_rms_sigma"]))
    return candidates


def plots(out, report):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(9, 6), layout="constrained")
    for ax, parameter in zip(axes.flat, ("log_rho", "log_q", "log_s", "t_E"), strict=True):
        for cadence, profiles in report["profiles"].items():
            points = [(row["value"], row["best_chi2"]) for row in profiles[parameter]
                      if row["best_chi2"] is not None]
            if points:
                x, y = np.array(points).T
                ax.plot(x, y-y.min(), marker="o", label=cadence)
        ax.set(xlabel=parameter, ylabel="Δχ² from sampled minimum")
    axes[0, 0].legend()
    fig.savefig(out/"profiles.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    for run in report["blind"]:
        x = [row["nfev"] for row in run["history"]]
        y = [row["chi2"] for row in run["history"]]
        settings = run["configured"]
        ax.semilogy(x, y, label=f'{settings["seed"]} / {settings["generations"]} generations')
    ax.set(xlabel="Objective evaluations", ylabel="Best dense training χ²")
    ax.legend()
    fig.savefig(out/"blind-convergence.png", dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(CONFIG_2.read_text())
    prior = json.loads(SETTINGS.read_text())
    baseline = json.loads(CONFIG.read_text())
    catalog = ROOT.parent/"examples/public_data/data/1093.json"
    scales = np.asarray(prior["recovery_tolerances"])
    bounds = np.asarray(baseline["bounds"], dtype=float)
    bounds[3] = [prior["log_q_edges"][0], prior["log_q_edges"][-1]]
    bounds[4] = np.log10([prior["s_edges"][0], prior["s_edges"][-1]])
    loaded = load(catalog, baseline)
    times = {key: group[0] for key, group in loaded.items()}
    lo, hi = cfg["historical_holdout"]
    masks = {key: (t < lo) | (t >= hi) for key, t in times.items()}
    center = cfg["dense_center"]
    outer, inner = cfg["dense_outer_days"], cfg["dense_inner_days"]
    dense = np.unique(np.concatenate([np.linspace(center-outer, center+outer, cfg["dense_outer_count"]),
                                      np.linspace(center-inner, center+inner, cfg["dense_inner_count"])]))
    dense_mask = np.arange(len(dense)) % cfg["dense_holdout_stride"] != 0
    manifest = dict(configured=cfg, effective=dict(bounds=bounds.tolist(), dense_n=len(dense),
                                                  injection_count=len(prior["injections"])),
                    sources=dict(cadence_sha256=sha(catalog), frozen_settings_sha256=sha(SETTINGS),
                                 legacy_settings_sha256=sha(CONFIG)),
                    implementation={path.name: sha(path) for path in
                                    (Path(__file__), ROOT/"binary_search.py", ROOT/"structured_recovery.py")},
                    versions=dict(numpy=np.__version__, scipy=scipy.__version__, mulensmodel=mm.__version__),
                    runtime=dict(benchmark_parallel_workers=1), datasets={})
    atomic(args.out/"manifest.json", manifest)
    rng = np.random.default_rng(cfg["noise_seed"])
    summary = dict(injections=[], nulls=[])
    for index, truth in enumerate(prior["injections"], 1):
        directory = args.out/f"injection-{index}"
        directory.mkdir()
        full = simulate(times, masks, truth, "finite", cfg, rng)
        reduced = reduce(full, cfg["reduced_stride"])
        ideal = simulate({"synthetic": dense}, {"synthetic": dense_mask}, truth, "finite", cfg)
        data = dict(full=full, reduced=reduced, dense=ideal)
        identities = {name: sample.identity() for name, sample in data.items()}
        manifest["datasets"][directory.name] = identities
        atomic(args.out/"manifest.json", manifest)
        report = dict(truth=truth, input=identities, configured=cfg,
                      effective=dict(datasets=identities), frozen_tolerances=scales.tolist(),
                      at_truth={name: sample.evaluate(truth, "finite") for name, sample in data.items()},
                      blind=[], profiles={}, local={}, geometry={})
        for seed in cfg["global_seeds"]:
            for generations in cfg["global_generations"]:
                run = annotate(blind(ideal, "finite", bounds, seed, generations, cfg["population_multiplier"]),
                               truth, scales)
                report["blind"].append(run)
                atomic(directory/f"blind-seed{seed}-g{generations}.json", run)
        good = [run for run in report["blind"] if run["valid"]]
        alternate = min(good, key=lambda run: run["scores"]["training_chi2"])["p"] if good else truth
        for name, sample in (("full", full), ("reduced", reduced)):
            budgets = cfg["injection_3_evaluations"] if index == 3 else [cfg["injection_3_evaluations"][0]]
            report["local"][name] = [annotate(local(sample, truth, bounds, scales, budget), truth, scales)
                                     for budget in budgets]
            report["profiles"][name] = profile(sample, truth, bounds, scales, cfg, alternate)
        competing = {}
        for label, edge in (("close", 1), ("wide", 0)):
            restricted = bounds.copy()
            restricted[4, edge] = -1e-6 if label == "close" else 1e-6
            start = np.asarray(truth).copy()
            start[4] = np.clip(-abs(start[4]) if label == "close" else abs(start[4]), *restricted[4])
            competing[label] = annotate(local(ideal, start, restricted, scales,
                                              cfg["injection_3_evaluations"][-1]), truth, scales)
        report["geometry"] = geometry_comparison(ideal, truth, competing, cfg)
        plots(directory, report)
        atomic(directory/"report.json", report)
        summary["injections"].append(dict(injection=index, blind_passes=sum(run.get("frozen_pass", False)
                                                                          for run in report["blind"]),
                                           blind_runs=len(report["blind"])))
        print(f"Completed injection {index}", flush=True)

    generation_budget = cfg["global_generations"][-1]
    for seed in cfg["null_seeds"]:
        reference = prior["injections"][0][:3]
        data = simulate({"synthetic": dense}, {"synthetic": dense_mask}, reference, "single", cfg,
                        np.random.default_rng(seed))
        single = blind(data, "single", bounds[:3], seed, generation_budget, cfg["population_multiplier"])
        # A poorly optimized null baseline can manufacture an apparent binary improvement.
        single_local = least_squares(lambda p: data.residual(p, "single"), single["p"],
                                     bounds=(bounds[:3, 0], bounds[:3, 1]), max_nfev=50)
        single["refinement"] = dict(p=single_local.x.tolist(), nfev=single_local.nfev,
                                    success=bool(single_local.success), scores=data.evaluate(single_local.x, "single"))
        binary = blind(data, "finite", bounds, seed, generation_budget, cfg["population_multiplier"])
        binary["refinement"] = local(data, binary["p"], bounds, scales, cfg["injection_3_evaluations"][-1])
        valid = single["refinement"]["success"] and binary["valid"]
        delta = None
        flagged = None
        if valid:
            s = single["refinement"]["scores"]
            b = binary["scores"]
            refined = binary["refinement"]
            if refined["valid"] and refined["scores"]["training_chi2"] < b["training_chi2"]:
                b = refined["scores"]
            delta = {key: s[key] - b[key] for key in s}
            flagged = bool(delta["training_chi2"] >= cfg["null_training_improvement_threshold"]
                           and delta["holdout_chi2"] > cfg["null_holdout_improvement_threshold"])
        report = dict(seed=seed, input=data.identity(), single=single, binary=binary, delta=delta, flagged=flagged)
        manifest["datasets"][f"null-seed{seed}"] = report["input"]
        atomic(args.out/"manifest.json", manifest)
        atomic(args.out/f"null-seed{seed}.json", report)
        summary["nulls"].append(dict(seed=seed, flagged=flagged, delta=delta))
        print(f"Completed null {seed}", flush=True)
    assessed = [run for run in summary["nulls"] if run["flagged"] is not None]
    if assessed:
        positives = sum(run["flagged"] for run in assessed)
        interval = binomtest(positives, len(assessed)).proportion_ci()
        summary["false_positive_screen"] = dict(positives=positives, assessed=len(assessed),
                                                exact_95pct_interval=[interval.low, interval.high])
    atomic(args.out/"summary.json", summary)


if __name__ == "__main__":
    main()
