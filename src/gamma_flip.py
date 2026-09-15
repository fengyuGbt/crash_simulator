"""Gamma flip: why the spiral stops (V9-P5).

V9-P1/P4 model the dealer short-gamma spiral: a selloff forces mechanical
delta-hedge selling, which pushes prices down further -- the market
manufacturing its own tail. That loop is self-amplifying but NOT
self-sustaining: in real crashes it terminates. The classic mechanism is
the GAMMA FLIP -- as implied volatility spikes, dealer positions flip
from short gamma (forced to sell into the fall) to long gamma (buying
the dip becomes mechanically attractive), and the spiral is cut.

This module adds one evolution rule to the P1 kernel:

    gamma_t starts at gamma_0 (short, negative)
    once cumulative drawdown passes flip_threshold,
        gamma_t converges toward flip_target (positive) at flip_speed

Everything else is the Part-5 kernel. Optional Monte Carlo shell
(same priors as V9-P4 plus an uncertain flip threshold) shows the
effect on the outcome distribution.

This is a MECHANISM model: the flip rule is a documented, configurable
stylization (vol-spike -> position flip), not a calibrated fit.

Usage:
    python3 gamma_flip.py                 # single-path comparison
    python3 gamma_flip.py --mc            # distribution with uncertain inputs
    python3 gamma_flip.py --self-test     # validate invariants
"""

import argparse
import random

try:
    import dealer_gamma
except ImportError:  # pragma: no cover
    dealer_gamma = None

# --- kernel parameters (mirror dealer_gamma) --------------------------------
DEFAULT_ALPHA = 0.6
DEFAULT_KAPPA = 1.0
DEFAULT_BETA = 0.15
DEFAULT_STEPS = 12
DEFAULT_SHOCK = -0.05

# --- flip rule (new in P5) ---------------------------------------------------
DEFAULT_GAMMA0 = -0.666           # initial short gamma (Part-5 estimate)
DEFAULT_FLIP_THRESHOLD = 0.10     # |drawdown| that triggers the flip
DEFAULT_FLIP_TARGET = 0.80        # gamma converges to +0.80 (deep long gamma)
DEFAULT_FLIP_SPEED = 0.60         # per-step convergence toward target

# --- Monte Carlo priors (V9-P4 style) ---------------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260915
DEFAULT_THRESH_MEAN = 0.10
DEFAULT_THRESH_SIGMA = 0.03
DEFAULT_THRESH_LO, DEFAULT_THRESH_HI = 0.04, 0.20
# gamma0 / shock priors identical to mc_mechanism (V9-P4)
DEFAULT_GAMMA_MEAN = -0.666
DEFAULT_GAMMA_SIGMA = 0.15
DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI = -1.0, 0.0
DEFAULT_SHOCK_MEAN = -0.05
DEFAULT_SHOCK_SIGMA = 0.02
DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI = -0.12, -0.01


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def run_flip(shock=DEFAULT_SHOCK, gamma0=DEFAULT_GAMMA0,
             flip_threshold=DEFAULT_FLIP_THRESHOLD,
             flip_target=DEFAULT_FLIP_TARGET,
             flip_speed=DEFAULT_FLIP_SPEED,
             alpha=DEFAULT_ALPHA, kappa=DEFAULT_KAPPA,
             beta=DEFAULT_BETA, n_steps=DEFAULT_STEPS,
             intervention=None):
    """Iterate the spiral with a gamma that flips after a drawdown threshold.

    Returns dict: amplification, total_return, flip_step (None if never
    flipped), gamma_path, price_path.
    """
    ret = shock
    price = 1.0
    price_path = [price]
    gamma_path = [gamma0]
    gamma = gamma0
    flip_step = None
    cumulative = 0.0
    active_intervention = 0

    for step in range(n_steps):
        # 1) flip rule: once drawdown passes threshold, gamma converges
        #    toward the (positive) target -- vol spike flips dealer book
        if flip_step is None and (price - 1.0) <= -flip_threshold:
            flip_step = step
        if flip_step is not None:
            gamma = gamma + flip_speed * (flip_target - gamma)

        # 2) same kernel as P1
        hedge_flow = -kappa * gamma * ret
        cumulative += ret
        if intervention is not None:
            if -cumulative >= intervention["trigger_pct"]:
                active_intervention = intervention["steps"]
        if active_intervention > 0:
            hedge_flow += intervention["size"]
            active_intervention -= 1
        ret_next = alpha * ret + beta * hedge_flow

        gamma_path.append(round(gamma, 6))
        price = price * (1.0 + ret)
        price_path.append(round(price, 6))
        ret = ret_next

    total_return = price - 1.0
    amplification = abs(total_return) / abs(shock) if shock != 0 else float("nan")
    return {
        "shock_size": shock,
        "gamma0": gamma0,
        "flip_threshold": flip_threshold,
        "flip_step": flip_step,
        "amplification": round(amplification, 3),
        "total_return": round(total_return, 4),
        "gamma_path": gamma_path,
        "price_path": price_path,
    }


def sample_inputs(rng):
    """Draw one (gamma0, shock, threshold) triple from the priors."""
    gamma0 = _clip(rng.gauss(DEFAULT_GAMMA_MEAN, DEFAULT_GAMMA_SIGMA),
                   DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI)
    shock = _clip(rng.gauss(DEFAULT_SHOCK_MEAN, DEFAULT_SHOCK_SIGMA),
                  DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI)
    thresh = _clip(rng.gauss(DEFAULT_THRESH_MEAN, DEFAULT_THRESH_SIGMA),
                   DEFAULT_THRESH_LO, DEFAULT_THRESH_HI)
    return gamma0, shock, thresh


def run_mc(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED):
    """Monte Carlo: uncertain gamma0/shock/threshold -> drawdown distribution."""
    rng = random.Random(seed)
    drops = []
    flip_counts = 0
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        res = run_flip(shock=shock, gamma0=gamma0, flip_threshold=thresh)
        drops.append(res["total_return"])
        if res["flip_step"] is not None:
            flip_counts += 1
    drops.sort()

    def q(p):
        return drops[min(len(drops) - 1, int(p * (len(drops) - 1)))]

    return {
        "n": n,
        "seed": seed,
        "p50": round(q(0.50), 4),
        "p10": round(q(0.10), 4),
        "p1": round(q(0.01), 4),
        "worst": round(drops[0], 4),
        "mean": round(sum(drops) / n, 4),
        "flip_share": round(flip_counts / n, 4),
    }


def threshold_sweep():
    """Amplification vs flip threshold: later flips hurt more."""
    rows = []
    for thresh in (0.05, 0.08, 0.10, 0.15, 0.20, 1.00):
        res = run_flip(flip_threshold=thresh)
        rows.append((thresh, res["total_return"], res["amplification"],
                     res["flip_step"]))
    return rows


def self_test():
    """Validate invariants: no-flip reproduces P1; flip cuts the spiral;
    later thresholds hurt more; MC tail is shallower with the flip."""
    print("== gamma_flip self-test ==")
    assert dealer_gamma is not None, "dealer_gamma import failed"

    # 1. no flip (threshold never reached) reproduces the Part-5 baseline
    no_flip = run_flip(flip_threshold=1.00)
    ref = dealer_gamma.run_spiral(DEFAULT_SHOCK, DEFAULT_GAMMA0)
    assert abs(no_flip["amplification"] - ref["amplification"]) < 0.01, (
        f"no-flip must match P1: {no_flip['amplification']} vs "
        f"{ref['amplification']}")
    assert no_flip["flip_step"] is None, "threshold 1.0 must never flip"

    # 2. flip cuts the spiral
    flip = run_flip()
    assert flip["flip_step"] is not None, "default threshold should flip"
    assert flip["amplification"] < no_flip["amplification"], (
        f"flip must cut amplification: {flip['amplification']} >= "
        f"{no_flip['amplification']}")

    # 3. gamma actually changes sign (short -> long)
    assert flip["gamma_path"][-1] > 0.0, (
        f"gamma must end positive after flip: {flip['gamma_path'][-1]}")

    # 4. later thresholds hurt more (monotone sweep)
    rows = threshold_sweep()
    amps = [r[2] for r in rows]
    assert all(amps[i] <= amps[i + 1] for i in range(len(amps) - 1)), (
        f"amplification must be monotone in threshold: {amps}")

    # 5. determinism
    again = run_flip()
    assert again["price_path"] == flip["price_path"], "non-deterministic run"

    # 6. MC: flip makes the tail shallower vs the no-flip distribution
    mc = run_mc()
    rng = random.Random(DEFAULT_SEED)
    drops_no = []
    for _ in range(mc["n"]):
        gamma0, shock, _ = sample_inputs(rng)
        drops_no.append(run_flip(shock=shock, gamma0=gamma0,
                                 flip_threshold=1.00)["total_return"])
    drops_no.sort()
    p1_no = drops_no[min(mc["n"] - 1, int(0.01 * (mc["n"] - 1)))]
    assert mc["p1"] > p1_no, (
        f"flip must shallow the p1 tail: {mc['p1']} <= {p1_no}")
    assert 0.0 < mc["flip_share"] < 1.0, (
        f"flip_share out of range: {mc['flip_share']}")

    print(f"  no-flip (P1 baseline) : -5% shock, gamma {DEFAULT_GAMMA0} -> "
          f"{no_flip['total_return']:.4f} ({no_flip['amplification']:.2f}x)")
    print(f"  flip (threshold {DEFAULT_FLIP_THRESHOLD})     : -> "
          f"{flip['total_return']:.4f} ({flip['amplification']:.2f}x), "
          f"flip at step {flip['flip_step']}, gamma ends "
          f"{flip['gamma_path'][-1]:+.2f}")
    print(f"  threshold sweep       : " + ", ".join(
        f"thr {r[0]:.2f} -> {r[1]:.4f} ({r[2]:.2f}x, flip@{r[3]})" for r in rows))
    print(f"  MC (n={mc['n']})        : p50 {mc['p50']} | p10 {mc['p10']} | "
          f"p1 {mc['p1']} | worst {mc['worst']} | flip in "
          f"{mc['flip_share']:.0%} of paths")
    print(f"  no-flip MC p1         : {round(p1_no, 4)} (tail shallower with flip)")
    print("== self-test OK ==")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Gamma flip: why the spiral stops")
    parser.add_argument("--self-test", action="store_true",
                        help="validate invariants")
    parser.add_argument("--mc", action="store_true",
                        help="run Monte Carlo distribution")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    no_flip = run_flip(flip_threshold=1.00)
    flip = run_flip()
    print("== gamma flip: single path ==")
    print(f"  no-flip (P1 baseline): {no_flip['total_return']:.4f} "
          f"({no_flip['amplification']:.2f}x)")
    print(f"  flip (threshold {DEFAULT_FLIP_THRESHOLD}): "
          f"{flip['total_return']:.4f} ({flip['amplification']:.2f}x), "
          f"flip at step {flip['flip_step']}")
    print(f"  gamma path: " + " -> ".join(f"{g:+.2f}" for g in
                                          flip["gamma_path"]))
    print("  threshold sweep (later flip = more damage):")
    for thresh, tr, amp, step in threshold_sweep():
        tag = "(never)" if step is None else f"step {step}"
        print(f"    threshold {thresh:>5}: {tr:>8.4f} ({amp:.2f}x)  flip {tag}")

    if args.mc:
        mc = run_mc()
        print("== Monte Carlo (uncertain gamma0/shock/threshold) ==")
        print(f"  p50 {mc['p50']} | p10 {mc['p10']} | p1 {mc['p1']} | "
              f"worst {mc['worst']} | mean {mc['mean']}")
        print(f"  flip fired in {mc['flip_share']:.0%} of paths")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
