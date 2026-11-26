# E003 parameter-blind exploratory recovery
No published planetary parameters are supplied. Event identity is known, so not a fully blind discovery. Frozen repository JSON hash required. Ground only; no parallax, limb darkening, orbital motion or correlated likelihood. Nonnegative flux fit on training data only, including flux normalization. Common two-day interleaved time blocks across instruments. Fold 0 is a pilot; do not tune on its test score. Five folds are exploratory CV, not an untouched external test. Compare seeds using training scores only. Full-data fit (--fold -1) has no test statistic. Checkpoints are generation logs, not resumable state. Optimizer success and boundary sensitivity must be reviewed. Synthetic tests check forward calculation and flux recovery, not global parameter recovery. No scientific execution claimed until bartOS outputs are reviewed.
From analysis:
    python -m pytest -q
    caffeinate -i python -u binary_search.py --fold 0 --iterations 20 --population 6 --seed 1093
    caffeinate -i python -u binary_search.py --fold 0 --iterations 250 --population 15 --seed 2026
    caffeinate -i python -u binary_search.py --fold 0 --iterations 250 --population 15 --seed 2027
    caffeinate -i python -u binary_search.py --mode finite --fold 0 --iterations 150 --population 15 --seed 2028
    python plot_binary_results.py results/E003/point_fold0_seed1093_g20_p6.json
Run remaining folds with fixed settings before comparing held-out scores. Preserve environment, git revision, logs and reports. No main merge.
