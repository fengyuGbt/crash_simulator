"""Margin cascade vs gamma flip (V9-P6).

Part 9 showed the gamma flip truncates the dealer spiral. But the flip
is not instant -- and before the book turns positive, leveraged
accounts are being force-liquidated in a cascade. The real question is
a RACE: does the flip arrive in time, or does the cascade run ahead of
it? (March 2020: many funds did not survive to the bottom.)

This module adds leveraged-account liquidation cascades to the
Part-5 kernel (gamma spiral + flip):

    price falls
      -> margin buckets trip (leverage, weight, trigger drawdown)
      -> forced selling hits the market (persistent, decaying flow)
      -> price falls further
      -> next bucket trips
      -> meanwhile the gamma flip is converging

Two engines, one race. Outputs: total drawdown, buckets liquidated,
flip step vs last-liquidation step, cascade share of the damage.

This is a MECHANISM model: bucket structure, sell share and impact are
documented, configurable stylizations, not calibrated fits.

Usage:
    python3 cascade.py                 # single-path comparison
    python3 cascade.py --mc            # distribution with uncertain inputs
    python3 cascade.py --self-test     # validate invariants
"""

import argparse
import random

try:
    import gamma_flip
except ImportError:  # pragma: no cover
    gamma_flip = None

# --- kernel parameters (mirror P1/P5) ---------------------------------------
DEFAULT_ALPHA = 0.6
DEFAULT_KAPPA = 1.0
DEFAULT_BETA = 0.15
DEFAULT_STEPS = 12
DEFAULT_SHOCK = -0.05
DEFAULT_GAMMA0 = -0.666

# --- flip rule (P5) ----------------------------------------------------------
DEFAULT_FLIP_THRESHOLD = 0.10
DEFAULT_FLIP_TARGET = 0.80
DEFAULT_FLIP_SPEED = 0.60

# --- cascade (new in P6) -----------------------------------------------------
# margin buckets: (leverage, portfolio weight, trigger drawdown)
DEFAULT_BUCKETS = [
    (10.0, 0.10, 0.05),
    (5.0, 0.20, 0.10),
    (3.0, 0.30, 0.15),
    (2.0, 0.40, 0.20),
]
DEFAULT_SELL_SHARE = 0.40     # forced sale fraction of a triggered bucket
DEFAULT_IMPACT = 0.40         # price impact per unit of forced flow
DEFAULT_FLOW_DECAY = 0.70     # persistence of cascade selling
DEFAULT_LAG_STEPS = 3         # forced liquidation releases over N steps
                              # (margin call -> grace window -> forced sale)

# --- Monte Carlo priors ------------------------------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260916
DEFAULT_THRESH_MEAN = 0.10
DEFAULT_THRESH_SIGMA = 0.03
DEFAULT_THRESH_LO, DEFAULT_THRESH_HI = 0.04, 0.20
DEFAULT_GAMMA_MEAN = -0.666
DEFAULT_GAMMA_SIGMA = 0.15
DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI = -1.0, 0.0
DEFAULT_SHOCK_MEAN = -0.05
DEFAULT_SHOCK_SIGMA = 0.02
DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI = -0.12, -0.01


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def run_cascade(shock=DEFAULT_SHOCK, gamma0=DEFAULT_GAMMA0,
                flip_threshold=DEFAULT_FLIP_THRESHOLD,
                flip_target=DEFAULT_FLIP_TARGET,
                flip_speed=DEFAULT_FLIP_SPEED,
                buckets=None, sell_share=DEFAULT_SELL_SHARE,
                impact=DEFAULT_IMPACT, flow_decay=DEFAULT_FLOW_DECAY,
                lag_steps=DEFAULT_LAG_STEPS,
                alpha=DEFAULT_ALPHA, kappa=DEFAULT_KAPPA,
                beta=DEFAULT_BETA, n_steps=DEFAULT_STEPS):
    """Iterate spiral + flip + margin cascade.

    Triggered buckets release their forced selling over `lag_steps`
    (margin-call grace window) rather than in one shot, so the cascade
    keeps feeding the market while the gamma flip converges.

    Returns dict: amplification, total_return, flip_step,
    last_liquidation_step, buckets_liquidated, cascade_share,
    price_path, cascade_flow_path.
    """
    buckets = list(buckets) if buckets is not None else list(DEFAULT_BUCKETS)
    fired = [False] * len(buckets)

    ret = shock
    price = 1.0
    price_path = [price]
    gamma = gamma0
    flip_step = None
    cascade_flow = 0.0
    cascade_flow_path = []
    last_liquidation_step = None
    total_liquidated_weight = 0.0
    releases = []          # each: [amount_per_step, steps_remaining]
    lag = max(1, lag_steps)

    for step in range(n_steps):
        drawdown = price - 1.0

        # 1) cascade: trip buckets whose trigger the current drawdown passes
        new_weight = 0.0
        for i, (lev, w, trig) in enumerate(buckets):
            if not fired[i] and drawdown <= -trig:
                fired[i] = True
                new_weight += w
                total_liquidated_weight += w
                last_liquidation_step = step
        if new_weight > 0:
            releases.append([new_weight * sell_share / lag, lag])

        # release this step's forced selling (decayed residual from before)
        flow_this = sum(r[0] for r in releases if r[1] > 0)
        cascade_flow = cascade_flow * flow_decay + flow_this
        for r in releases:
            if r[1] > 0:
                r[1] -= 1

        # 2) gamma flip (P5 rule)
        if flip_step is None and drawdown <= -flip_threshold:
            flip_step = step
        if flip_step is not None:
            gamma = gamma + flip_speed * (flip_target - gamma)

        # 3) kernel: dealer hedge + cascade flow (cascade SELLS: negative impact)
        hedge_flow = -kappa * gamma * ret
        total_flow = hedge_flow - cascade_flow * impact
        ret_next = alpha * ret + beta * total_flow

        cascade_flow_path.append(round(cascade_flow, 6))
        price = price * (1.0 + ret)
        price_path.append(round(price, 6))
        ret = ret_next

    total_return = price - 1.0
    amplification = abs(total_return) / abs(shock) if shock != 0 else float("nan")

    # cascade share: run the same path WITHOUT the cascade (spiral+flip only).
    # Only computed when buckets exist; an empty-bucket run has no cascade.
    cascade_share = 0.0
    if buckets:
        solo = run_cascade(shock=shock, gamma0=gamma0,
                           flip_threshold=flip_threshold,
                           flip_target=flip_target, flip_speed=flip_speed,
                           buckets=[], sell_share=sell_share, impact=impact,
                           flow_decay=flow_decay, lag_steps=lag,
                           alpha=alpha, kappa=kappa, beta=beta,
                           n_steps=n_steps)
        solo_loss = abs(solo["total_return"])
        total_loss = abs(total_return)
        cascade_share = ((total_loss - solo_loss) / total_loss
                         if total_loss > 0 else 0.0)

    return {
        "shock_size": shock,
        "gamma0": gamma0,
        "flip_threshold": flip_threshold,
        "flip_step": flip_step,
        "buckets_liquidated": sum(fired),
        "total_liquidated_weight": round(total_liquidated_weight, 4),
        "last_liquidation_step": last_liquidation_step,
        "cascade_share": round(cascade_share, 4),
        "amplification": round(amplification, 3),
        "total_return": round(total_return, 4),
        "price_path": price_path,
        "cascade_flow_path": cascade_flow_path,
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
    buckets_hit = []
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        res = run_cascade(shock=shock, gamma0=gamma0, flip_threshold=thresh)
        drops.append(res["total_return"])
        buckets_hit.append(res["buckets_liquidated"])
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
        "avg_buckets_hit": round(sum(buckets_hit) / n, 2),
    }


def self_test():
    """Validate invariants: spiral baseline reproduces P5; cascade adds
    damage; early flip saves buckets; monotone in impact; determinism;
    MC tail deeper with cascade."""
    print("== cascade self-test ==")
    assert gamma_flip is not None, "gamma_flip import failed"

    # 1. no buckets + threshold 1.0 == no cascade, no flip -> P1 baseline
    bare = run_cascade(flip_threshold=1.00, buckets=[])
    ref = gamma_flip.run_flip(flip_threshold=1.00)
    assert abs(bare["amplification"] - ref["amplification"]) < 0.01, (
        f"bare run must match P1: {bare['amplification']} vs "
        f"{ref['amplification']}")
    assert bare["buckets_liquidated"] == 0, "no buckets must not liquidate"

    # 2. adding the cascade deepens the damage (and it's not all flip)
    cascade = run_cascade()
    assert cascade["buckets_liquidated"] > 0, "default buckets should trip"
    assert cascade["total_return"] < gamma_flip.run_flip(
        flip_threshold=cascade["flip_threshold"])["total_return"], (
        "cascade must add damage beyond spiral+flip")
    assert cascade["cascade_share"] > 0.0, "cascade share must be positive"

    # 3. early flip saves buckets vs late flip
    early = run_cascade(flip_threshold=0.05)
    late = run_cascade(flip_threshold=0.20)
    assert early["buckets_liquidated"] < late["buckets_liquidated"], (
        f"early flip must liquidate fewer buckets: "
        f"{early['buckets_liquidated']} >= {late['buckets_liquidated']}")
    assert (late["flip_step"] is None) or (late["flip_step"] > early["flip_step"]), (
        f"late flip must not arrive before early flip: "
        f"late {late['flip_step']} early {early['flip_step']}")

    # 4. monotone in impact: more market impact -> deeper loss
    lo = run_cascade(impact=0.10)
    hi = run_cascade(impact=0.40)
    assert hi["total_return"] < lo["total_return"], (
        f"more impact must deepen loss: {hi['total_return']} >= "
        f"{lo['total_return']}")

    # 5. determinism
    again = run_cascade()
    assert again["price_path"] == cascade["price_path"], "non-deterministic run"

    # 6. MC: cascade tail is deeper than the flip-only distribution
    mc = run_mc()
    rng = random.Random(DEFAULT_SEED)
    drops_no = []
    for _ in range(mc["n"]):
        gamma0, shock, thresh = sample_inputs(rng)
        drops_no.append(run_cascade(shock=shock, gamma0=gamma0,
                                    flip_threshold=thresh,
                                    buckets=[])["total_return"])
    drops_no.sort()
    p1_no = drops_no[min(mc["n"] - 1, int(0.01 * (mc["n"] - 1)))]
    assert mc["p1"] < p1_no, (
        f"cascade must deepen the p1 tail: {mc['p1']} >= {p1_no}")
    assert 1 <= mc["avg_buckets_hit"] <= len(DEFAULT_BUCKETS), (
        f"avg buckets hit out of range: {mc['avg_buckets_hit']}")

    print(f"  bare (P1 baseline)        : {bare['total_return']:.4f} "
          f"({bare['amplification']:.2f}x)")
    print(f"  flip only (threshold {DEFAULT_FLIP_THRESHOLD}): "
          f"{gamma_flip.run_flip()['total_return']:.4f} "
          f"({gamma_flip.run_flip()['amplification']:.2f}x)")
    print(f"  flip + cascade            : {cascade['total_return']:.4f} "
          f"({cascade['amplification']:.2f}x), "
          f"{cascade['buckets_liquidated']}/{len(DEFAULT_BUCKETS)} buckets, "
          f"cascade share {cascade['cascade_share']:.0%}")
    print(f"  early flip (5%)           : "
          f"{early['buckets_liquidated']} buckets, "
          f"{early['total_return']:.4f} | late flip (20%): "
          f"{late['buckets_liquidated']} buckets, "
          f"{late['total_return']:.4f}")
    print(f"  impact sweep              : 0.10 -> {lo['total_return']:.4f} | "
          f"0.40 -> {hi['total_return']:.4f}")
    print(f"  MC (n={mc['n']})        : p50 {mc['p50']} | p10 {mc['p10']} | "
          f"p1 {mc['p1']} | worst {mc['worst']} | avg {mc['avg_buckets_hit']} "
          f"buckets")
    print(f"  no-cascade MC p1         : {round(p1_no, 4)} (cascade deepens tail)")
    print("== self-test OK ==")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Margin cascade vs gamma flip")
    parser.add_argument("--self-test", action="store_true",
                        help="validate invariants")
    parser.add_argument("--mc", action="store_true",
                        help="run Monte Carlo distribution")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    bare = run_cascade(flip_threshold=1.00, buckets=[])
    solo = run_cascade()
    cascade = run_cascade()
    print("== cascade vs flip: single path ==")
    print(f"  bare (no cascade, no flip): {bare['total_return']:.4f} "
          f"({bare['amplification']:.2f}x)")
    print(f"  spiral+flip only           : {solo['total_return']:.4f} "
          f"({solo['amplification']:.2f}x), flip@step {solo['flip_step']}")
    print(f"  flip + cascade             : {cascade['total_return']:.4f} "
          f"({cascade['amplification']:.2f}x), "
          f"{cascade['buckets_liquidated']}/{len(DEFAULT_BUCKETS)} buckets, "
          f"last liquidation step {cascade['last_liquidation_step']}, "
          f"flip@step {cascade['flip_step']}")
    print(f"  cascade share of damage    : {cascade['cascade_share']:.0%}")

    print("  threshold sweep (flip timing vs cascade):")
    for thresh in (0.05, 0.08, 0.10, 0.15, 0.20, 1.00):
        r = run_cascade(flip_threshold=thresh)
        flip_tag = f"flip@{r['flip_step']}" if r["flip_step"] is not None \
            else "no flip"
        print(f"    threshold {thresh:>5}: {r['total_return']:>8.4f} "
              f"({r['amplification']:.2f}x)  {r['buckets_liquidated']}/"
              f"{len(DEFAULT_BUCKETS)} buckets  {flip_tag}  last liq "
              f"{r['last_liquidation_step']}")

    if args.mc:
        mc = run_mc()
        print("== Monte Carlo (uncertain gamma0/shock/threshold) ==")
        print(f"  p50 {mc['p50']} | p10 {mc['p10']} | p1 {mc['p1']} | "
              f"worst {mc['worst']} | mean {mc['mean']}")
        print(f"  avg {mc['avg_buckets_hit']} of "
              f"{len(DEFAULT_BUCKETS)} buckets liquidated per path")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
