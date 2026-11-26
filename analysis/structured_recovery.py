"""Run E003.1 with fixed, training-only ranking and resumable batches."""
import argparse
import fcntl
import hashlib
import json
import math
from pathlib import Path

import MulensModel as mm
import numpy as np
import scipy
from scipy.optimize import differential_evolution, minimize, nnls

from binary_search import CONFIG, ROOT, atomic, load, prepare

PENALTY = 1e30
SETTINGS = ROOT / "experiments/E003_1/config.json"


def make_model(p, kind, coords, times):
    parameters = dict(t_0=p[0]+2450000, u_0=p[1], t_E=p[2])
    if kind in ("point", "finite"):
        parameters.update(q=10**p[3], s=10**p[4], alpha=p[5] % 360)
    if kind == "parallax":
        parameters.update(pi_E_N=p[3], pi_E_E=p[4], t_0_par=2457560.)
    if kind == "finite":
        parameters["rho"] = 10**p[6]
    model = mm.Model(parameters, coords=coords)
    if kind == "parallax":
        model.parallax(earth_orbital=True, satellite=False, topocentric=False)
    if kind == "finite":
        model.set_magnification_methods([float(times.min()-1), "VBM", float(times.max()+1)])
    return model


def magnify(p, kind, coords, time):
    jd = time + 2450000
    result = make_model(p, kind, coords, jd).get_magnification(jd)
    if np.any(~np.isfinite(result) | (result <= 0)):
        raise ValueError("Invalid magnification")
    return result


def loss(z, df):
    square = z**2
    return square if df is None else (df+1)*np.log1p(square/df)


def evaluate(p, groups, kind, coords=None, df=None, details=False):
    total, instruments = 0., {}
    for name, (t, f, e, train) in groups.items():
        if not train.any():
            continue
        use = slice(None) if details else train
        a = magnify(p, kind, coords, t[use])
        design = np.column_stack((a, np.ones(len(a)))) / e[use, None]
        observed = f[use] / e[use]
        fit = train if details else slice(None)
        x, y = design[fit], observed[fit]
        coeff = nnls(x, y)[0]
        if df is not None:
            def robust(c):
                z = y-x@c
                return loss(z, df).sum(), -2*(df+1)*(x.T @ (z/(df+z*z)))
            fitted = minimize(robust, coeff, jac=True, bounds=[(0, None)]*2, method="L-BFGS-B")
            if not fitted.success:
                raise ValueError(fitted.message)
            coeff = fitted.x
        z = observed-design@coeff
        total += loss(z[fit], df).sum()
        if details:
            test = z[~train]
            adjacent = (~train[:-1]) & (~train[1:]) & (np.diff(t) < 0.1)
            left, right = z[:-1][adjacent], z[1:][adjacent]
            correlation = np.corrcoef(left, right)[0, 1] if len(left) > 2 and min(left.std(), right.std()) > 0 else None
            instruments[name] = dict(train_loss=float(loss(z[train], df).sum()),
                                     test_loss=float(loss(test, df).sum()), flux=coeff.tolist(),
                                     time=t.tolist(), train=train.tolist(), residual=z.tolist(),
                                     test_adjacent_pairs=len(left), test_correlation=correlation)
    return instruments if details else float(total)


def optimize(label, groups, kind, bounds, seed, out, cfg, coords=None, df=None, start=None):
    checkpoint = out / f"{label}.json"
    state = json.loads(checkpoint.read_text()) if checkpoint.exists() else dict(generations=0, batches=[])
    if state.get("done"):
        return state

    def objective(p):
        try:
            return evaluate(p, groups, kind, coords, df)
        except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError):
            return PENALTY

    while not state.get("done"):
        generation = state["generations"]
        budget = min(cfg["checkpoint_generations"], cfg["iterations"]-generation)
        result = differential_evolution(
            objective, bounds, rng=np.random.default_rng([seed, generation]),
            maxiter=budget, popsize=cfg["population"], x0=start if generation == 0 else None,
            init=state.get("population", "latinhypercube"), tol=cfg["tolerance"], polish=False,
        )
        if not np.isfinite(result.fun) or result.fun >= PENALTY:
            raise RuntimeError(f"No valid candidate for {label}")
        previous = state.get("loss", PENALTY)
        if result.fun <= previous:
            state.update(p=result.x.tolist(), loss=float(result.fun))
        state["generations"] += result.nit
        state["batches"].append(dict(generation=state["generations"], loss=state["loss"]))
        state.update(population=result.population.tolist(), converged=bool(result.success),
                     done=bool(result.success or state["generations"] >= cfg["iterations"]))
        if state["done"] and kind == "finite":
            refined = minimize(objective, state["p"], bounds=bounds, method="Powell",
                               options={"maxiter": cfg["local_iterations"]})
            if np.isfinite(refined.fun) and refined.fun < state["loss"]:
                state.update(p=refined.x.tolist(), loss=float(refined.fun))
            state["local_converged"] = bool(refined.success)
        atomic(checkpoint, state)
    return state


def search(groups, out, base, cfg, baseline, df=None):
    candidates = []
    for qi, (qlo, qhi) in enumerate(zip(cfg["log_q_edges"], cfg["log_q_edges"][1:])):
        for si, (slo, shi) in enumerate(zip(cfg["s_edges"], cfg["s_edges"][1:])):
            bounds = base[:3] + [[qlo, qhi], [math.log10(slo), math.log10(shi)], base[5]]
            for seed in cfg["seeds"]:
                label = f"q{qi}_s{si}_seed{seed}"
                rng = np.random.default_rng([seed, qi, si])
                start = baseline + [rng.uniform(low, high) for low, high in bounds[3:]]
                state = optimize(label, groups, "point", bounds, seed, out, cfg, df=df, start=start)
                candidates.append(dict(label=label, p=state["p"], loss=state["loss"],
                                       converged=state["converged"]))
    candidates.sort(key=lambda candidate: candidate["loss"])
    finite = []
    full = base[:3] + [[cfg["log_q_edges"][0], cfg["log_q_edges"][-1]],
                       [math.log10(cfg["s_edges"][0]), math.log10(cfg["s_edges"][-1])]] + base[5:]
    seen = set()
    for candidate in candidates:
        cell = candidate["label"].rsplit("_", 1)[0]
        if cell in seen:
            continue
        seen.add(cell)
        state = optimize("finite_"+candidate["label"], groups, "finite", full, cfg["seeds"][0],
                         out, cfg, df=df, start=candidate["p"]+[sum(base[6])/2])
        finite.append(dict(label=candidate["label"], p=state["p"], loss=state["loss"]))
        if len(finite) == cfg["refine_count"]:
            break
    return candidates, sorted(finite, key=lambda candidate: candidate["loss"])


def plot_geometry(p, groups, out):
    import matplotlib.pyplot as plt

    t0, _, te = p[:3]
    times = np.linspace(t0-0.25*te, t0+0.25*te, 1000) + 2450000
    model = make_model(p, "finite", None, times)
    trajectory = model.get_trajectory(times)
    fig, ax = plt.subplots()
    model.plot_caustics(n_points=12000, color="black")
    ax.plot(trajectory.x, trajectory.y, label="Source trajectory")
    for name, (t, _, _, train) in groups.items():
        near = (~train) & (abs(t-t0) < 0.25*te)
        if near.any():
            observed = model.get_trajectory(t[near]+2450000)
            ax.scatter(observed.x, observed.y, s=3, label=name)
    center = model.get_trajectory([t0+2450000])
    ax.add_patch(plt.Circle((center.x[0], center.y[0]), 10**p[6], fill=False, color="tab:blue"))
    ax.set(xlabel="x / Einstein radius", ylabel="y / Einstein radius", aspect="equal")
    ax.legend()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def run_fit(groups, out, base, cfg, coords=None, df=None, plot=False):
    out.mkdir(parents=True, exist_ok=True)
    seed = cfg["seeds"][0]
    single = optimize("single", groups, "single", base[:3], seed, out, cfg, df=df)
    point, finite = search(groups, out, base, cfg, single["p"], df)
    choices = dict(single=single, point=point[0], finite=finite[0])
    if coords is not None:
        bounds = base[:3]+[cfg["parallax_component_bounds"]]*2
        choices["parallax"] = optimize("parallax", groups, "parallax", bounds, seed, out, cfg, coords, df)
    models = {kind: dict(p=v["p"], training_loss=v["loss"],
                         instruments=evaluate(v["p"], groups, kind, coords, df, True))
              for kind, v in choices.items()}
    if plot:
        plot_geometry(finite[0]["p"], groups, out/"caustics.png")
    return dict(models=models, point_candidates=point, finite_candidates=finite)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["synthetic", "fit", "exclude", "parallax"])
    parser.add_argument("--input", type=Path, default=ROOT.parent/"examples/public_data/data/1093.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--holdout", nargs=2, type=float, metavar=("START", "END"))
    parser.add_argument("--test-jd", type=Path, help="Per-instrument arrays of verified full geocentric JD TDB")
    parser.add_argument("--coords", help="ICRS coordinates as sexagesimal RA and Dec")
    parser.add_argument("--instrument")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.mode != "synthetic" and (args.holdout is None or not args.holdout[0] < args.holdout[1]):
        parser.error("Supply a predeclared, increasing --holdout interval in native reduced HJD")
    if args.mode == "parallax" and (args.test_jd is None or not args.coords):
        parser.error("Parallax needs verified geocentric JD TDB and ICRS coordinates")
    if args.mode != "parallax" and (args.test_jd is not None or args.coords):
        parser.error("--test-jd and --coords are for parallax")
    cfg, base_config = json.loads(SETTINGS.read_text()), json.loads(CONFIG.read_text())
    base = base_config["bounds"]
    raw = load(args.input, base_config)
    if args.mode == "exclude" and args.instrument not in raw:
        parser.error("Supply a valid --instrument")
    groups = prepare(raw, -1, base_config)
    if args.smoke:
        cfg.update(log_q_edges=[-6, -1], s_edges=[0.3, 3.0], seeds=[761], iterations=1,
                   population=2, local_iterations=1, refine_count=1, injections=cfg["injections"][:1])
        groups = {name: tuple(array[::30] for array in group) for name, group in groups.items()}
    args.out.mkdir(parents=True, exist_ok=True)
    lock = (args.out/".run.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("This output directory already has an active run")
    manifest = dict(mode=args.mode, smoke=args.smoke, holdout=args.holdout, instrument=args.instrument,
                    coords=args.coords, input_hash=base_config["sha256"], settings=cfg,
                    time_hash=hashlib.sha256(args.test_jd.read_bytes()).hexdigest() if args.test_jd else None,
                    versions=[np.__version__, scipy.__version__, mm.__version__],
                    implementation={file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                                    for file in (Path(__file__), ROOT/"binary_search.py", CONFIG)})
    manifest_file = args.out/"manifest.json"
    if manifest_file.exists() and json.loads(manifest_file.read_text()) != manifest:
        parser.error("Use a new output directory for changed settings, input, or implementation")
    atomic(manifest_file, manifest)
    if args.mode == "synthetic":
        injections = []
        rng = np.random.default_rng(3329)
        for i, truth in enumerate(cfg["injections"]):
            injected = {}
            for name, (t, _, _, _) in groups.items():
                flux = .6*magnify(truth, "finite", None, t)+.4
                error = flux*.015
                train = (t < 7585) | (t >= 7587)
                injected[name] = t, flux+rng.normal(scale=error), error, train
            directory = args.out/f"injection_{i}"
            result = run_fit(injected, directory, base, cfg)
            recovered = result["models"]["finite"]["p"]
            differences = abs(np.array(recovered)-truth)
            differences[5] = abs((recovered[5]-truth[5]+180)%360-180)
            injections.append(dict(truth=truth, recovered=recovered, errors=differences.tolist(),
                               passes=bool(np.all(differences <= cfg["recovery_tolerances"])),
                               fit=result))
        report = dict(injections=injections, all_pass=all(item["passes"] for item in injections))
    else:
        times = json.loads(args.test_jd.read_text()) if args.test_jd else None
        if times is not None and args.smoke:
            times = {name: values[::30] for name, values in times.items()}
        if times is not None and set(times) != set(groups):
            parser.error("Time file must contain exactly the modeled instruments")
        training, excluded = {}, None
        lo, hi = args.holdout
        for name, (native, mag, err) in ({k: tuple(a[::30] for a in v) for k,v in raw.items()} if args.smoke else raw).items():
            train = (native < lo) | (native >= hi)
            t = native
            if times is not None:
                t = np.asarray(times[name], dtype=float)-2450000
                if t.shape != native.shape or not np.isfinite(t).all() or np.any(abs(t-native) > .02) or np.any(np.diff(t) <= 0):
                    parser.error(f"Invalid or misaligned JD TDB arrays for {name}")
            if args.mode == "exclude" and name == args.instrument:
                peak_lo, peak_hi = cfg["calibration_exclusion_days"]
                train &= (native < peak_lo) | (native >= peak_hi)
            if train.sum() < 2:
                parser.error(f"Insufficient training/calibration observations for {name}")
            f = 10**(-.4*(mag-np.median(mag[train])))
            group = t, f, .4*np.log(10)*f*err, train
            if args.mode == "exclude" and name == args.instrument:
                excluded = group
            else:
                training[name] = group
        if not any((~group[3]).any() for group in training.values()):
            parser.error("No physical-model holdout observations")
        report = {}
        for label, df in (("gaussian", None), ("student_t", cfg["student_df"])):
            result = run_fit(training, args.out/label, base, cfg, args.coords, df, plot=True)
            if excluded is not None:
                group = excluded
                in_holdout = (group[0] >= lo) & (group[0] < hi)
                keep = group[3] | in_holdout
                if not in_holdout.any():
                    parser.error("Excluded instrument has no observations in the holdout")
                result["excluded_instrument"] = {
                    kind: evaluate(model["p"], {args.instrument: tuple(a[keep] for a in group)}, kind,
                                   args.coords, df, True)[args.instrument]
                    for kind, model in result["models"].items()
                }
            report[label] = result
    atomic(args.out/"report.json", report)


if __name__ == "__main__":
    main()
