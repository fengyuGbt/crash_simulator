"""Mechanism -> Monte Carlo -> outcome distribution (V9-P4).

Response to reader feedback on Part 5/6: a -5% shock should produce a
DISTRIBUTION of outcomes, not a single 3.07x amplification factor.

The V9 mechanism layer (dealer_gamma.py, discrete_margin.py) is
deterministic by design: it answers WHAT STRUCTURE produces the tail.
This module wraps the dealer-gamma spiral in a Monte Carlo shell and
lets parameter uncertainty become outcome uncertainty:

  - net_gamma is ESTIMATED from state (VIX/SKEW percentiles), not
    observed (no OCC data)           ->  sample it
  - the shock size is a SCENARIO, not a fact  ->  sample it
  - N paths -> max drawdown distribution -> p50/p10/p1 + EP curve

The single 3.07x number from Part 5 is not a forecast; it is the
location of ONE path inside a distribution. This module shows where
that path sits, and what the tail looks like when the uncertainty is
made explicit. An optional intervention runs the same distribution
with the 2020-style flow cut, to show the effect on the tail.

This is a MECHANISM + UNCERTAINTY model: the kernel is the documented
deterministic spiral; the sampling distributions are documented,
configurable priors, not calibrated fits.

Usage:
    python3 mc_mechanism.py                 # distribution demo + EP curve
    python3 mc_mechanism.py --self-test     # validate invariants
"""

import argparse
import random

try:
    import dealer_gamma
except ImportError:  # pragma: no cover - allow local run without src on path
    dealer_gamma = None

# --- sampling priors (documented, configurable) ------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260914
# net gamma: estimated -0.666 from SKEW 0.833 percentile; treat as noisy
DEFAULT_GAMMA_MEAN = -0.666
DEFAULT_GAMMA_SIGMA = 0.15
DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI = -1.0, 0.0     # state implies short gamma
# shock: -5% is a scenario, not a fact; sample around it
DEFAULT_SHOCK_MEAN = -0.05
DEFAULT_SHOCK_SIGMA = 0.02
DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI = -0.12, -0.01

# thresholds for the exceedance-probability (EP) curve
EP_THRESHOLDS = [-0.05, -0.08, -0.10, -0.12, -0.15, -0.20]


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def sample_inputs(rng):
    """Draw one (net_gamma, shock) pair from the documented priors."""
    gamma = _clip(rng.gauss(DEFAULT_GAMMA_MEAN, DEFAULT_GAMMA_SIGMA),
                  DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI)
    shock = _clip(rng.gauss(DEFAULT_SHOCK_MEAN, DEFAULT_SHOCK_SIGMA),
                  DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI)
    return gamma, shock


def run_path(rng, intervention=None):
    """One Monte Carlo path: sample inputs, run the deterministic spiral."""
    gamma, shock = sample_inputs(rng)
    res = dealer_gamma.run_spiral(shock, gamma, intervention=intervention)
    return res["total_return"], res["amplification"], gamma, shock


def run_mc(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED, intervention=None):
    """Run N paths; return sorted drawdowns, percentiles and EP curve."""
    rng = random.Random(seed)          # deterministic, no numpy dependency
    paths = []
    for _ in range(n):
        total_return, amp, gamma, shock = run_path(rng, intervention)
        paths.append((total_return, amp, gamma, shock))

    drops = sorted(p[0] for p in paths)   # ascending (worst first)

    def q(p):
        """p-th quantile of drawdowns (p=0.01 -> worse than 99% of paths)."""
        return drops[min(len(drops) - 1, int(p * (len(drops) - 1)))]

    ep = {str(x): round(sum(1 for d in drops if d <= x) / n, 4)
          for x in EP_THRESHOLDS}

    return {
        "n": n,
        "seed": seed,
        "p50": round(q(0.50), 4),
        "p10": round(q(0.10), 4),
        "p1": round(q(0.01), 4),
        "worst": round(drops[0], 4),
        "mean": round(sum(drops) / n, 4),
        "ep": ep,
        "paths": paths,
    }


def deterministic_reference():
    """The Part-5 single path: -5% shock, gamma -0.666, no sampling."""
    res = dealer_gamma.run_spiral(DEFAULT_SHOCK_MEAN, DEFAULT_GAMMA_MEAN)
    return res


def self_test():
    """Validate distribution invariants (deterministic under same seed)."""
    print("== mc_mechanism self-test ==")
    assert dealer_gamma is not None, "dealer_gamma import failed"

    base = run_mc()
    ref = deterministic_reference()

    # 1. determinism
    again = run_mc()
    assert [p[0] for p in base["paths"]] == [p[0] for p in again["paths"]], (
        "same seed must reproduce the same paths")

    # 2. ordering: tail percentiles are deeper than the median
    assert base["p1"] < base["p10"] < base["p50"] < 0.0, (
        f"tail ordering broken: p1 {base['p1']} p10 {base['p10']} p50 {base['p50']}")

    # 3. EP curve is monotone: deeper thresholds are rarer
    eps = [v for _, v in sorted(base["ep"].items(), key=lambda kv: -float(kv[0]))]
    assert all(eps[i] >= eps[i + 1] for i in range(len(eps) - 1)), (
        f"EP curve not monotone: {base['ep']}")

    # 4. the single 3.07x reference sits INSIDE the distribution, near the
    #    median of outcomes (it is a representative path, not a tail event)
    ref_drop = ref["total_return"]
    assert base["p10"] <= ref_drop <= base["p50"], (
        f"reference path outside expected band: {ref_drop} "
        f"(p50 {base['p50']}, p10 {base['p10']})")
    # reference should be closer to the median than to the p10 tail
    assert abs(ref_drop - base["p50"]) <= abs(base["p10"] - base["p50"]) * 0.5, (
        f"reference {ref_drop} too far from median {base['p50']} "
        f"(p10 {base['p10']})")

    # 5. intervention cuts the tail: worst and p1 are shallower
    inter = run_mc(intervention=dict(dealer_gamma.DEFAULT_INTERVENTION))
    assert inter["p1"] > base["p1"], (
        f"intervention must shallow the tail: {inter['p1']} <= {base['p1']}")
    assert inter["worst"] > base["worst"], (
        f"intervention must shallow the worst: {inter['worst']} <= {base['worst']}")

    print(f"  reference single path      : {ref['shock_size']} shock, gamma "
          f"{ref['net_gamma']} -> {ref['total_return']:.4f} "
          f"({ref['amplification']:.2f}x)")
    print(f"  distribution (n={base['n']})   : p50 {base['p50']} | "
          f"p10 {base['p10']} | p1 {base['p1']} | worst {base['worst']} | "
          f"mean {base['mean']}")
    print(f"  reference inside band      : {base['p10']} <= "
          f"{ref_drop} <= {base['p50']}  (OK)")
    print(f"  EP curve                   : {base['ep']}")
    print(f"  intervention (tail)        : p1 {base['p1']} -> {inter['p1']}, "
          f"worst {base['worst']} -> {inter['worst']}")
    print("== self-test OK ==")
    return 0


def print_result(res, intervention=False):
    label = " (with 2020-style flow cut)" if intervention else ""
    print(f"== mechanism Monte Carlo{label} ==")
    print(f"  paths: {res['n']}  seed: {res['seed']}")
    print(f"  drawdown  p50: {res['p50']}  p10: {res['p10']}  "
          f"p1: {res['p1']}  worst: {res['worst']}  mean: {res['mean']}")
    print("  EP curve (P(drawdown <= x)):")
    for k, v in res["ep"].items():
        print(f"    {k:>7}: {v}")


def main():
    parser = argparse.ArgumentParser(
        description="Mechanism Monte Carlo: outcome distribution")
    parser.add_argument("--self-test", action="store_true",
                        help="validate distribution invariants")
    parser.add_argument("--n", type=int, default=DEFAULT_N_PATHS,
                        help="number of paths")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="random seed")
    parser.add_argument("--intervention", action="store_true",
                        help="run with the flow-cut intervention")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    base = run_mc(args.n, args.seed)
    ref = deterministic_reference()
    print_result(base)
    print(f"\n  Part-5 single path: {ref['shock_size']} shock, gamma "
          f"{ref['net_gamma']} -> {ref['total_return']:.4f} "
          f"({ref['amplification']:.2f}x)")
    print(f"  -> that single path is a point INSIDE the distribution "
          f"(between p10 {base['p10']} and p50 {base['p50']})")

    if args.intervention:
        inter = run_mc(args.n, args.seed,
                       intervention=dict(dealer_gamma.DEFAULT_INTERVENTION))
        print_result(inter, intervention=True)
        print(f"  -> intervention shallows the tail: p1 {base['p1']} -> "
              f"{inter['p1']}, worst {base['worst']} -> {inter['worst']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
