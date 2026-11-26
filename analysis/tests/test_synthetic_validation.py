import numpy as np
import pytest

from structured_recovery import evaluate
from synthetic_validation import reduce, simulate


CONFIG = dict(source_flux=.6, blend_flux=.4, noise_fraction=.015)


def test_reduced_data_reuses_the_same_noise_and_membership():
    times = {"test": np.linspace(7550, 7580, 41)}
    masks = {"test": np.arange(41) % 4 != 0}
    full = simulate(times, masks, [7560., .03, 50.], "single", CONFIG, np.random.default_rng(7))
    reduced = reduce(full, 3)
    for actual, source in zip(reduced.groups["test"], full.groups["test"], strict=True):
        np.testing.assert_array_equal(actual, source[::3])
    assert reduced.identity()["sha256"] != full.identity()["sha256"]


def test_objective_agrees_with_e0031_and_missing_holdout_is_null():
    times = {"first": np.linspace(7558, 7563, 70), "second": np.linspace(7556, 7565, 55)}
    masks = {name: np.ones(len(t), dtype=bool) for name, t in times.items()}
    truth = [7560., .03, 50., -3., -.11, 46., -3.]
    data = simulate(times, masks, truth, "finite", CONFIG, np.random.default_rng(2))
    assert data.objective(truth, "finite") == pytest.approx(evaluate(truth, data.groups, "finite"))
    assert data.evaluate(truth, "finite")["holdout_chi2"] is None
