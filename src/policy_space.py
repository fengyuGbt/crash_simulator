# -*- coding: utf-8 -*-
"""V10-P6: policy space depletion — the backstop's clock.

Part 12 priced the twenty-day window *inside* a crisis. This module
prices the policy space *across* crises: the backstop is not an
unlimited resource, and markets know it.

Capacity C in [0,1] maps to two things:

  1. trigger probability p(C):  the chance the backstop actually fires
     on a given path (its "ammunition");
  2. market leverage (mu_lam, sigma_lam):  how much and how uncertainly
     leverage rises as capacity drains.  Leverage is booked on the
     promise of protection; protection is probabilistic.

Key structure: leverage is deterministic (the policy commitment),
protection is probabilistic (the policy capacity).  As C falls, the
same high-leverage book faces a smaller chance of rescue — that is the
clock running down.

Deterministic: same seed, same shocks, same numbers every run.
"""
import argparse
import random

from policy_moral_hazard import (
    DEFAULT_N_PATHS,
    DEFAULT_SEED,
    _clip,
    run_policy_moral_hazard,
    sample_inputs,
)

# capacity -> (trigger_prob, lam_mean, lam_sigma)
# C=1.0: fully credible backstop, mild leverage, certain trigger
# C=0.0: no backstop at all; market never believed one existed, so
#        leverage returns to the exogenous 1.0 (reproduces P4's
#        no-backstop world)
SPACE_LEVELS = [
    (1.00, 1.00, 1.35, 0.25),
    (0.75, 0.75, 1.50, 0.30),
    (0.50, 0.50, 1.75, 0.35),
    (0.25, 0.25, 2.00, 0.40),
    (0.00, 0.00, 1.00, 0.00),
]

THRESHOLD_DEFAULT = 0.30  # 30% drawdown cascade zone


def run_mc(capacity, n=DEFAULT_N_PATHS, seed=DEFAULT_SEED,
           threshold=THRESHOLD_DEFAULT):
    """One policy-space level: trigger_prob + market leverage from C."""
    trigger_prob, lam_mean, lam_sigma = _space_params(capacity)
    rng = random.Random(seed)
    losses = []
    fires = 0
    betrayed = 0
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        lam = lam_mean
        if lam_sigma > 0:
            lam = _clip(rng.gauss(lam_mean, lam_sigma), 1.0, 2.5)
        trigger = rng.random() < trigger_prob
        kwargs = dict(shock=shock, gamma0=gamma0, flip_threshold=thresh,
                      leverage_multiplier=lam, rng=rng)
        if trigger:
            # backstop fires per the default P4 rules
            pass
        else:
            # betrayed path: leverage booked on the promise, but the
            # backstop never fires (policy capacity exhausted)
            kwargs["trigger_buckets"] = 99
            if lam_mean > 1.0:
                betrayed += 1
        res = run_policy_moral_hazard(**kwargs)
        losses.append(res["total_return"])
        if res["backstop_step"] is not None:
            fires += 1
    losses.sort()

    mean = sum(losses) / n
    p10 = losses[min(n - 1, int(0.10 * (n - 1)))]
    p1 = losses[min(n - 1, int(0.01 * (n - 1)))]
    worst = losses[0]
    jump_share = sum(1.0 for x in losses if -x >= threshold) / n

    return {
        "capacity": capacity,
        "trigger_prob": trigger_prob,
        "lam_mean": lam_mean,
        "lam_sigma": lam_sigma,
        "mean": round(mean, 4),
        "p10": round(p10, 4),
        "p1": round(p1, 4),
        "worst": round(worst, 4),
        "jump_share": round(jump_share, 4),
        "fire_share": round(fires / n, 4),
        "betrayed_share": round(betrayed / n, 4),
    }


def _space_params(capacity):
    for cap, prob, mu, sig in SPACE_LEVELS:
        if abs(capacity - cap) < 1e-9:
            return prob, mu, sig
    raise ValueError("capacity must be one of %s"
                     % [c for c, _, _, _ in SPACE_LEVELS])


def space_table():
    return [run_mc(cap) for cap, _, _, _ in SPACE_LEVELS]


def self_test():
    print("== policy_space self-test ==")

    # boundary: C=0 reproduces the P4 no-backstop world
    c0 = run_mc(0.0)
    assert abs(c0["mean"] + 0.3413) < 0.005, c0
    assert abs(c0["p10"] + 0.4101) < 0.005
    assert abs(c0["p1"] + 0.4394) < 0.005
    print("   C=0 reproduces no-backstop world OK (mean=%.4f)" % c0["mean"])

    # monotonicity: over the "believed" range (C=1.0 -> 0.25) lower
    # capacity never improves the tail
    rows = space_table()
    believed = rows[:-1]
    for a, b in zip(believed, believed[1:]):
        assert a["p1"] >= b["p1"], (a["capacity"], b["capacity"])
        assert a["jump_share"] <= b["jump_share"] + 1e-9
    print("   tail monotone over believed range (1.0->0.25) OK")

    # signature feature: half-believed is WORSE than never-believed.
    # C=0.25 books leverage on a 25% promise; C=0 books nothing, so
    # leverage returns to the exogenous 1.0. The depleted-but-trusted
    # backstop does more damage than the absent one.
    assert rows[-2]["p1"] <= rows[-1]["p1"] + 1e-9, (
        rows[-2]["p1"], rows[-1]["p1"])
    assert rows[-2]["mean"] <= rows[-1]["mean"] + 1e-9
    print("   half-believed worse than never-believed OK "
          "(p1 %.4f vs %.4f)" % (rows[-2]["p1"], rows[-1]["p1"]))

    # determinism
    assert run_mc(0.5) == run_mc(0.5)
    print("   determinism OK")

    # betrayal logic: with capacity in (0,1), some paths hold leverage
    # without protection (the believed-but-depleted levels only; C=0
    # never believed, so it is not betrayal)
    for row in rows[1:-1]:
        assert row["betrayed_share"] > 0
    print("   betrayal share positive for 0<C<1 OK")

    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true",
                    help="run invariants only")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P6: policy space depletion (backstop's clock) ==")
    print("capacity -> (trigger prob, market leverage lam distribution)")
    for cap, prob, mu, sig in SPACE_LEVELS:
        print("   C=%.2f  trigger=%.0f%%  lam~N(%.2f,%.2f)%s"
              % (cap, prob * 100, mu, sig,
                 "  (no backstop)" if cap == 0 else ""))

    rows = space_table()
    print()
    print("%-7s%8s%9s%9s%9s%8s%10s%9s" %
          ("C", "mean", "p10", "p1", "worst", "fire%", ">30%", "betray%"))
    for r in rows:
        print("%-7.2f%8.4f%9.4f%9.4f%9.4f%8.1f%10.1f%9.1f" %
              (r["capacity"], r["mean"], r["p10"], r["p1"], r["worst"],
               r["fire_share"] * 100, r["jump_share"] * 100,
               r["betrayed_share"] * 100))

    full = rows[0]
    zero = rows[-1]

    def tail_cost(r):
        return r["p1"] - full["p1"]

    def mean_cost(r):
        return r["mean"] - full["mean"]

    print()
    print("clock readings (vs C=1.0 full capacity):")
    for r in rows[1:]:
        print("   C=%.2f  mean drifts %.1f pts | p1 drifts %.1f pts "
              "| >30%% share %.1f%%"
              % (r["capacity"], mean_cost(r) * 100, tail_cost(r) * 100,
                 r["jump_share"] * 100))

    print()
    print("half-believed is worse than never-believed:")
    print("   C=0.25 (leverage booked, 25%% protection) p1=%.4f vs "
          "C=0.00 (no promise, no leverage) p1=%.4f"
          % (rows[-2]["p1"], rows[-1]["p1"]))
    print("   the tail moves first, the headline last;")
    print("   and the most dangerous policy space is the one that is")
    print("   believed but depleted.")


if __name__ == "__main__":
    main()
