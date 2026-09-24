# -*- coding: utf-8 -*-
"""V10-P5: crisis cost nonlinearity.

Why 6 more points of tail cost far more than 6 points.

Takes the V10-P4 Monte Carlo loss distributions (exogenous vs
policy-endogenous leverage) and prices them under convex social-cost
functions:

  1. power cost   C(L) = (-L)^gamma            (gamma > 1)
  2. threshold    C(L) = -L + jump if -L >= threshold
                  (drawdown crossing a level fires cascade / political
                   aftershock costs that are not in the linear loss)

Shows two things:

  A. By a mean standard the backstop is a clean rescue; under convex
     cost the same rescue is smaller, and the share of the rescue eaten
     by endogenous leverage is larger than the mean-based share.
  B. Endogenous leverage pushes the 1st percentile across the threshold
     the policy promised to prevent: exogenous p1 sits inside the
     "no cascade" zone, policy-endogenous p1 crosses it.

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

GAMMA_DEFAULT = 2.0
THRESHOLD_DEFAULT = 0.30  # 30% drawdown
JUMP_DEFAULT = 0.50       # extra cost units when threshold is crossed


def power_cost(loss, gamma=GAMMA_DEFAULT):
    """Convex cost. loss=-0.31, gamma=2 -> 0.0961."""
    return (-loss) ** gamma


def threshold_cost(loss, threshold=THRESHOLD_DEFAULT, jump=JUMP_DEFAULT):
    """Linear loss plus a jump once the drawdown crosses the threshold."""
    base = -loss
    return base + jump if base >= threshold else base


def run_mc(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED, with_backstop=True,
           leverage_multiplier=1.0, lambda_stochastic=False,
           lam_mean=1.35, lam_sigma=0.25, lam_lo=1.0, lam_hi=2.0,
           gamma=GAMMA_DEFAULT, threshold=THRESHOLD_DEFAULT,
           jump=JUMP_DEFAULT):
    rng = random.Random(seed)
    losses = []
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        lam = leverage_multiplier
        if lambda_stochastic:
            lam = _clip(rng.gauss(lam_mean, lam_sigma), lam_lo, lam_hi)
        kwargs = dict(shock=shock, gamma0=gamma0, flip_threshold=thresh,
                      leverage_multiplier=lam, rng=rng)
        if not with_backstop:
            kwargs["trigger_buckets"] = 99
        res = run_policy_moral_hazard(**kwargs)
        losses.append(res["total_return"])
    losses.sort()

    mean = sum(losses) / n
    p10 = losses[min(n - 1, int(0.10 * (n - 1)))]
    p1 = losses[min(n - 1, int(0.01 * (n - 1)))]
    ec_power = sum(power_cost(x, gamma) for x in losses) / n
    ec_threshold = sum(threshold_cost(x, threshold, jump)
                       for x in losses) / n
    jump_share = sum(1.0 for x in losses if -x >= threshold) / n

    return {
        "n": n, "seed": seed, "with_backstop": with_backstop,
        "leverage_multiplier": leverage_multiplier,
        "lambda_stochastic": lambda_stochastic,
        "mean": round(mean, 4), "p10": round(p10, 4), "p1": round(p1, 4),
        "ec_power": round(ec_power, 4),
        "ec_threshold": round(ec_threshold, 4),
        "jump_share": round(jump_share, 4),
        "gamma": gamma, "threshold": threshold, "jump": jump,
    }


def comparison_table():
    rows = [
        ("no backstop, lambda=1.0",
         dict(with_backstop=False, leverage_multiplier=1.0)),
        ("backstop,  lambda=1.0",
         dict(with_backstop=True, leverage_multiplier=1.0)),
        ("backstop,  lam~N(1.35,0.25)",
         dict(with_backstop=True, lambda_stochastic=True,
              lam_mean=1.35, lam_sigma=0.25)),
        ("backstop,  lam~N(1.5,0.30)",
         dict(with_backstop=True, lambda_stochastic=True,
              lam_mean=1.5, lam_sigma=0.30)),
        ("backstop,  lam~N(1.75,0.35)",
         dict(with_backstop=True, lambda_stochastic=True,
              lam_mean=1.75, lam_sigma=0.35)),
    ]
    return [(label, run_mc(**kw)) for label, kw in rows]


def self_test():
    print("== crisis_cost_nonlinearity self-test ==")

    # convexity: E[C(L)] >= C(E[L]) for any non-degenerate distribution
    rng = random.Random(7)
    losses = []
    for _ in range(400):
        gamma0, shock, thresh = sample_inputs(rng)
        res = run_policy_moral_hazard(
            shock=shock, gamma0=gamma0, flip_threshold=thresh,
            leverage_multiplier=1.0, rng=rng)
        losses.append(res["total_return"])
    mean = sum(losses) / len(losses)
    ec = sum(power_cost(x, GAMMA_DEFAULT) for x in losses) / len(losses)
    assert ec >= power_cost(mean, GAMMA_DEFAULT) + 1e-9, (
        "Jensen: E[C(L)] must exceed C(E[L]) under convexity")
    print("   Jensen (convexity) OK: E[C(L)]=%.4f >= C(E[L])=%.4f"
          % (ec, power_cost(mean, GAMMA_DEFAULT)))

    # monotonicity: deeper loss -> higher cost under both cost functions
    assert power_cost(-0.31) > power_cost(-0.25)
    assert threshold_cost(-0.31) > threshold_cost(-0.25)
    assert threshold_cost(-0.29, 0.30, 0.50) == 0.29
    assert threshold_cost(-0.31, 0.30, 0.50) == 0.81
    print("   cost functions monotone & threshold jump OK")

    # determinism
    a = run_mc()
    b = run_mc()
    assert a == b
    print("   determinism OK")

    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true",
                    help="run invariants only")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P5: crisis cost nonlinearity ==")
    print("costs: C(L)=(-L)^%.1f  and  -L + %.2f jump beyond %.0f%% drawdown"
          % (GAMMA_DEFAULT, JUMP_DEFAULT, THRESHOLD_DEFAULT * 100))

    rows = comparison_table()
    print()
    print("%-26s%8s%8s%8s%10s%10s%8s" %
          ("scenario", "mean", "p10", "p1", "E[C^2]", "E[C_thr]", "jump%"))
    for label, r in rows:
        print("%-26s%8.4f%8.4f%8.4f%10.4f%10.4f%8.1f" %
              (label, r["mean"], r["p10"], r["p1"], r["ec_power"],
               r["ec_threshold"], r["jump_share"] * 100))

    # rescue accounting
    no = rows[0][1]
    ex = rows[1][1]
    end = rows[4][1]

    def rescue(x):
        return x["mean"] - no["mean"]

    def rescue_c(x):
        return x["ec_power"] - no["ec_power"]

    mean_rescue = rescue(ex)
    mean_eaten = rescue(ex) - rescue(end)
    c_rescue = rescue_c(ex)
    c_eaten = rescue_c(ex) - rescue_c(end)

    print()
    print("rescue (exogenous backstop vs no backstop):")
    print("   mean basis : %.1f pts rescue, %.1f pts eaten (%.0f%%)"
          % (mean_rescue * 100, mean_eaten * 100,
             mean_eaten / mean_rescue * 100))
    print("   convex basis: %.3f units rescue, %.3f eaten (%.0f%%)"
          % (c_rescue, c_eaten, c_eaten / c_rescue * 100))

    # threshold crossing
    print()
    print("threshold %.0f%% drawdown (cascade/aftershock zone):" %
          (THRESHOLD_DEFAULT * 100))
    for label, r in rows:
        print("   %-26s p1=%8.4f  jump_share=%5.1f%%"
              % (label, r["p1"], r["jump_share"] * 100))


if __name__ == "__main__":
    main()
