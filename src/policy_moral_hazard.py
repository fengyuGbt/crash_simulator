"""Policy moral hazard / leverage adaptation (V10-P4).

Parts 12-14 built the policy layer and made it endogenous:
  - V10-P1 (`policy_backstop.py`): the backstop is flow-based, truncates.
  - V10-P2 (`policy_expectations.py`): regime trigger + expectations
    channel -- the announcement cuts unfinished sell intentions.
  - V10-P3 (`policy_anticipation.py`): the market learns the rule and
    front-runs it; constructive ambiguity is a knob with an optimum.

Part 14 ended by asking what happens when the market learns that the
rule is fuzzy. This module makes the deeper point: **the market does not
have to learn the rule to break the policy -- it only has to learn that
a backstop exists.** If leveraged accounts believe the policy will cap
their losses, the equilibrium level of leverage rises, the same shock
lands on bigger books, and the tail the policy is trying to truncate is
the tail it helped build. This is the mechanism version of the
Greenspan/Fed put debate.

V10-P4 models leverage as a policy-endogenous variable: the bucket
weights are scaled by `leverage_multiplier` (lambda). The market has
learned that a backstop exists, so initial positions are bigger. The
backstop still fires and still truncates -- but it truncates a deeper
tail. The headline result is the crossover: at some lambda the
backstop-plus-leverage tail is NO better than no-backstop-at-low-
leverage, and beyond it the policy makes things worse. A stress test
that treats leverage as exogenous is structurally optimistic.

The kernel mirrors cascade.py / policy_backstop.py / policy_expectations.py
/ policy_anticipation.py; the additions are the leverage scaling and the
crossover scan.

Usage:
    python3 policy_moral_hazard.py           # comparison table + scan
    python3 policy_moral_hazard.py --mc      # distribution
    python3 policy_moral_hazard.py --self-test
"""

import argparse
import random

# --- kernel parameters (mirror V10-P1/P2) -----------------------------------
DEFAULT_ALPHA = 0.6
DEFAULT_KAPPA = 1.0
DEFAULT_BETA = 0.15
DEFAULT_STEPS = 40
DEFAULT_SHOCK = -0.05
DEFAULT_GAMMA0 = -0.666

DEFAULT_FLIP_THRESHOLD = 0.10
DEFAULT_FLIP_TARGET = 0.80
DEFAULT_FLIP_SPEED = 0.60

DEFAULT_BUCKETS = [
    (10.0, 0.10, 0.05),
    (5.0, 0.20, 0.10),
    (3.0, 0.30, 0.15),
    (2.0, 0.40, 0.20),
]
DEFAULT_SELL_SHARE = 0.40
DEFAULT_IMPACT = 0.40
DEFAULT_FLOW_DECAY = 0.85
DEFAULT_LAG_STEPS = 6

DEFAULT_TRIGGER_BUCKETS = 2
DEFAULT_TRIGGER_DRAWDOWN = 0.20
DEFAULT_COVERAGE = 1.0
DEFAULT_ABSORPTION_RAMP = 8
DEFAULT_EXPECTATION_EFFECT = 1.0

# --- moral hazard (P4) --------------------------------------------------------
DEFAULT_LEVERAGE_MULTIPLIER = 1.0   # lambda: 1.0 = exogenous leverage

# --- Monte Carlo priors ------------------------------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260921
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


def _scaled_buckets(leverage_multiplier=DEFAULT_LEVERAGE_MULTIPLIER):
    # Higher leverage = bigger book AND thinner margin: the same
    # drawdown trips the position earlier (trigger scaled by 1/lambda).
    lam = leverage_multiplier
    return [(lev, round(w * lam, 4), round(trig / lam, 4))
            for lev, w, trig in DEFAULT_BUCKETS]


def run_policy_moral_hazard(shock=DEFAULT_SHOCK, gamma0=DEFAULT_GAMMA0,
                            flip_threshold=DEFAULT_FLIP_THRESHOLD,
                            flip_target=DEFAULT_FLIP_TARGET,
                            flip_speed=DEFAULT_FLIP_SPEED,
                            buckets=None, sell_share=DEFAULT_SELL_SHARE,
                            impact=DEFAULT_IMPACT,
                            flow_decay=DEFAULT_FLOW_DECAY,
                            lag_steps=DEFAULT_LAG_STEPS,
                            alpha=DEFAULT_ALPHA, kappa=DEFAULT_KAPPA,
                            beta=DEFAULT_BETA, n_steps=DEFAULT_STEPS,
                            trigger_buckets=DEFAULT_TRIGGER_BUCKETS,
                            trigger_drawdown=DEFAULT_TRIGGER_DRAWDOWN,
                            coverage=DEFAULT_COVERAGE,
                            absorption_ramp=DEFAULT_ABSORPTION_RAMP,
                            expectation_effect=DEFAULT_EXPECTATION_EFFECT,
                            leverage_multiplier=DEFAULT_LEVERAGE_MULTIPLIER,
                            rng=None):
    """Iterate spiral + flip + margin cascade with regime-triggered
    backstop, expectations channel, and P4 leverage scaling.

    `leverage_multiplier` (lambda) scales the bucket weights: the market
    has learned a backstop exists, so books are bigger. lambda = 1.0
    reproduces V10-P2 exactly (exogenous leverage).
    """
    if buckets is None:
        buckets = _scaled_buckets(leverage_multiplier)
    else:
        buckets = [(lev, w, trig) for lev, w, trig in buckets]
    fired = [False] * len(buckets)
    rng = rng if rng is not None else random.Random(0)

    ret = shock
    price = 1.0
    price_path = [price]
    gamma = gamma0
    flip_step = None
    cascade_flow = 0.0
    cascade_flow_path = []
    last_liquidation_step = None
    total_liquidated_weight = 0.0
    releases = []
    lag = max(1, lag_steps)
    absorbed_flow = 0.0
    expected_flow_saved = 0.0
    backstop_step = None
    fired_at_fire = 0
    new_release_after_backstop = False

    for step in range(n_steps):
        drawdown = price - 1.0

        # regime trigger: the policy listens to the market
        fired_count = sum(fired)
        if (backstop_step is None
                and fired_count >= trigger_buckets
                and drawdown <= -trigger_drawdown):
            backstop_step = step
            fired_at_fire = fired_count
        backstop_active = backstop_step is not None

        # cascade: trip buckets whose trigger the drawdown passes
        new_weight = 0.0
        for i, (lev, w, trig) in enumerate(buckets):
            if not fired[i] and drawdown <= -trig:
                fired[i] = True
                new_weight += w
                total_liquidated_weight += w
                last_liquidation_step = step

        if new_weight > 0:
            release = new_weight * sell_share / lag
            releases.append([release, lag])
            if backstop_active and release * (1.0 - expectation_effect) > 0:
                new_release_after_backstop = True

        # release + expectations channel (P2)
        flow_intention = sum(r[0] for r in releases if r[1] > 0)
        if backstop_active and expectation_effect > 0:
            cut_intention = flow_intention * expectation_effect
            cut_stock = cascade_flow * expectation_effect
            expected_flow_saved += cut_intention + cut_stock
            flow_intention -= cut_intention
            cascade_flow -= cut_stock
        cascade_flow = cascade_flow * flow_decay + flow_intention
        for r in releases:
            if r[1] > 0:
                r[1] -= 1

        # absorption channel (P1), with stand-up ramp
        if backstop_active:
            ramp = max(0.0, min(1.0, (step - backstop_step)
                                / max(1, absorption_ramp)))
            absorb_rate = coverage * ramp
            absorbed = cascade_flow * absorb_rate
            cascade_flow -= absorbed
            absorbed_flow += absorbed

        # gamma flip (P5 rule)
        if flip_step is None and drawdown <= -flip_threshold:
            flip_step = step
        if flip_step is not None:
            gamma = gamma + flip_speed * (flip_target - gamma)

        # kernel
        hedge_flow = -kappa * gamma * ret
        total_flow = hedge_flow - cascade_flow * impact
        ret_next = alpha * ret + beta * total_flow

        cascade_flow_path.append(round(cascade_flow, 6))
        price = price * (1.0 + ret)
        price_path.append(round(price, 6))
        ret = ret_next

    total_return = price - 1.0
    amplification = abs(total_return) / abs(shock) if shock != 0 else float("nan")

    tail_truncated = (backstop_step is not None
                      and not new_release_after_backstop
                      and (absorbed_flow > 0 or expected_flow_saved > 0))

    return {
        "shock_size": shock,
        "gamma0": gamma0,
        "flip_threshold": flip_threshold,
        "flip_step": flip_step,
        "buckets_liquidated": sum(fired),
        "total_liquidated_weight": round(total_liquidated_weight, 4),
        "last_liquidation_step": last_liquidation_step,
        "amplification": round(amplification, 3),
        "total_return": round(total_return, 4),
        "backstop_step": backstop_step,
        "trigger_buckets_hit_at_fire": fired_at_fire,
        "absorbed_flow": round(absorbed_flow, 4),
        "expected_flow_saved": round(expected_flow_saved, 4),
        "tail_truncated": tail_truncated,
        "price_path": price_path,
        "cascade_flow_path": cascade_flow_path,
    }


def sample_inputs(rng):
    gamma0 = _clip(rng.gauss(DEFAULT_GAMMA_MEAN, DEFAULT_GAMMA_SIGMA),
                   DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI)
    shock = _clip(rng.gauss(DEFAULT_SHOCK_MEAN, DEFAULT_SHOCK_SIGMA),
                  DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI)
    thresh = _clip(rng.gauss(DEFAULT_THRESH_MEAN, DEFAULT_THRESH_SIGMA),
                   DEFAULT_THRESH_LO, DEFAULT_THRESH_HI)
    return gamma0, shock, thresh


def run_mc(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED,
           with_backstop=True, leverage_multiplier=1.0,
           lambda_stochastic=False, lam_mean=1.35, lam_sigma=0.25,
           lam_lo=1.0, lam_hi=2.0):
    rng = random.Random(seed)
    drops = []
    fires = 0
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
        drops.append(res["total_return"])
        if res["backstop_step"] is not None:
            fires += 1
    drops.sort()

    def q(p):
        return drops[min(len(drops) - 1, int(p * (len(drops) - 1)))]

    return {
        "n": n,
        "seed": seed,
        "with_backstop": with_backstop,
        "leverage_multiplier": leverage_multiplier,
        "lambda_stochastic": lambda_stochastic,
        "p50": round(q(0.50), 4),
        "p10": round(q(0.10), 4),
        "p1": round(q(0.01), 4),
        "worst": round(drops[0], 4),
        "mean": round(sum(drops) / n, 4),
        "fire_share": round(fires / n, 4),
    }


def comparison_table():
    rows = []
    for label, kw in (
        ("no backstop, lambda=1.0", dict(trigger_buckets=99,
                                          leverage_multiplier=1.0)),
        ("backstop,  lambda=1.0", dict(leverage_multiplier=1.0)),
        ("no backstop, lambda=1.5", dict(trigger_buckets=99,
                                         leverage_multiplier=1.5)),
        ("backstop,  lambda=1.5", dict(leverage_multiplier=1.5)),
    ):
        res = run_policy_moral_hazard(**kw)
        rows.append((label, res))
    return rows


def self_test():
    print("== policy_moral_hazard self-test ==")

    base_no = run_policy_moral_hazard(trigger_buckets=99,
                                      leverage_multiplier=1.0)
    assert base_no["backstop_step"] is None

    base_bs = run_policy_moral_hazard(leverage_multiplier=1.0)
    assert base_bs["backstop_step"] is not None

    # lambda=1.0 must reproduce V10-P2
    assert abs(base_no["total_return"] - (-0.3645)) < 0.002, (
        "no-backstop baseline drift")
    assert abs(base_bs["total_return"] - (-0.2277)) < 0.002, (
        "P2 baseline drift")

    # leverage is monotone: higher lambda, deeper tail (both regimes)
    no_l = [run_policy_moral_hazard(trigger_buckets=99,
                                    leverage_multiplier=x)["total_return"]
            for x in (1.0, 1.3, 1.6, 2.0)]
    bs_l = [run_policy_moral_hazard(
        leverage_multiplier=x)["total_return"]
        for x in (1.0, 1.3, 1.6, 2.0)]
    assert no_l == sorted(no_l, reverse=True), "leverage monotone (no bs)"
    assert bs_l == sorted(bs_l, reverse=True), "leverage monotone (bs)"

    # backstop still helps at every lambda (truncation is real)
    for x in (1.0, 1.3, 1.6, 2.0):
        a = run_policy_moral_hazard(trigger_buckets=99,
                                    leverage_multiplier=x)["total_return"]
        b = run_policy_moral_hazard(leverage_multiplier=x)["total_return"]
        assert b >= a, "backstop must truncate at every lambda"

    # determinism
    assert (run_policy_moral_hazard()["total_return"]
            == run_policy_moral_hazard()["total_return"])
    assert (run_policy_moral_hazard()["price_path"]
            == run_policy_moral_hazard()["price_path"])

    print("   lambda scan (single path):")
    print(f"   {'lambda':<8}{'no backstop':<14}{'backstop':<14}")
    for x in (1.0, 1.3, 1.6, 2.0):
        a = run_policy_moral_hazard(trigger_buckets=99,
                                    leverage_multiplier=x)["total_return"]
        b = run_policy_moral_hazard(leverage_multiplier=x)["total_return"]
        print(f"   {x:<8.2f}{a:<14.4f}{b:<14.4f}")
    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mc", action="store_true", help="run Monte Carlo")
    ap.add_argument("--self-test", action="store_true", help="run invariants")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P4: leverage as a policy-endogenous variable ==")
    rows = comparison_table()
    print(f"{'scenario':<28}{'return':<10}{'fire':<6}{'trunc'}")
    for name, res in rows:
        print(f"{name:<28}{res['total_return']:<10.4f}"
              f"{str(res['backstop_step']):<6}{str(res['tail_truncated']):<6}")

    print("\nleverage scan:")
    print(f"{'lambda':<8}{'no backstop':<14}{'backstop':<14}{'gap':<10}")
    base_no = run_policy_moral_hazard(trigger_buckets=99,
                                      leverage_multiplier=1.0)["total_return"]
    for x in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0):
        a = run_policy_moral_hazard(trigger_buckets=99,
                                    leverage_multiplier=x)["total_return"]
        b = run_policy_moral_hazard(leverage_multiplier=x)["total_return"]
        print(f"{x:<8.2f}{a:<14.4f}{b:<14.4f}"
              f"{(a - b):<10.4f}")

    if args.mc:
        print("\n== Monte Carlo (2000 paths, leverage exogenous vs endogenous) ==")
        for label, kw in (
            ("no bs, lam=1.0 (exog)", dict(with_backstop=False)),
            ("bs, lam=1.0 (exog)", dict(with_backstop=True)),
            ("bs, lam~N(1.35,0.25)", dict(with_backstop=True,
                                           lambda_stochastic=True)),
            ("bs, lam~N(1.5,0.30)", dict(with_backstop=True,
                                          lambda_stochastic=True,
                                          lam_mean=1.5, lam_sigma=0.30)),
            ("bs, lam~N(1.75,0.35)", dict(with_backstop=True,
                                           lambda_stochastic=True,
                                           lam_mean=1.75, lam_sigma=0.35)),
        ):
            mc = run_mc(**kw)
            print(f"  {label:<20} p1={mc['p1']:<9.4f} "
                  f"p10={mc['p10']:<9.4f} worst={mc['worst']:<9.4f} "
                  f"fire={mc['fire_share']}")


if __name__ == "__main__":
    main()
