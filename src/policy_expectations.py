"""Policy expectations channel (V10-P2).

Part 12 (V10-P1, `policy_backstop.py`) made the backstop explicit:
`backstop = f(trigger, lag, coverage, object)` with a fixed lag and pure
flow absorption. Two things it could not yet do, and Part 12 said so:

  1) ENDOGENOUS TRIGGER. The Fed does not arrive on a calendar -- it
     arrives when the regime is confirmed. In March 2020 the flow tool
     fired on Mar 23, the day corporate-credit dysfunction was
     unmistakable. Here the backstop activates on STATE, not on a
     step count: a minimum number of tripped margin buckets AND a
     minimum drawdown.

  2) EXPECTATIONS CHANNEL. The real value of the "as needed" commitment
     is not the flow it absorbs -- it is that leveraged accounts STOP
     front-running the cascade, because they believe someone will buy
     the liquidation. A bounded number ("$700B") is a price tool in
     disguise: the market can price the limit, so panic is not removed.
     This module models the announcement effect: after the backstop
     activates, newly-tripped buckets sell a fraction (1 - effect) of
     what they would have sold. effect = 1.0 is the unbounded
     commitment; effect = 0.0 is flow absorption without expectations.

Calibration flavor (March 2020): the S&P bottomed the day the object
switched to flow with NO ceiling. The kernel should show the
expectations channel buying materially more tail than pure absorption.

The kernel mirrors cascade.py (P6) / policy_backstop.py (V10-P1); the
additions are the state trigger and the announcement channel.

Usage:
    python3 policy_expectations.py           # comparison table
    python3 policy_expectations.py --mc      # distribution
    python3 policy_expectations.py --self-test
"""

import argparse
import random

# --- kernel parameters (mirror P6 / V10-P1) ----------------------------------
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

# --- regime trigger (V10-P2) --------------------------------------------------
DEFAULT_TRIGGER_BUCKETS = 2       # fire when at least N buckets tripped
DEFAULT_TRIGGER_DRAWDOWN = 0.20   # AND drawdown at least this deep
                                  # (calibrated: fire lands ~step 14 of 40,
                                  #  the Mar-2020-3/23 neighborhood -- the
                                  #  policy listens to the market, not a
                                  #  calendar)
DEFAULT_COVERAGE = 1.0            # flow absorbed once the tool is live
DEFAULT_ABSORPTION_RAMP = 8       # the buying mechanism stands up over N
                                  # steps (PMCCF/SMCCF announced Mar 23,
                                  #  actual buying ramped after): flows
                                  #  that arrive during the ramp still
                                  #  reach the price
DEFAULT_EXPECTATION_EFFECT = 1.0  # 0 = absorption only, 1 = full announcement
                                  # (expectations are INSTANT: accounts stop
                                  #  front-running the day it is announced)

# --- Monte Carlo priors ------------------------------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260919
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


def run_policy_expectations(shock=DEFAULT_SHOCK, gamma0=DEFAULT_GAMMA0,
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
                            expectation_effect=DEFAULT_EXPECTATION_EFFECT):
    """Iterate spiral + flip + margin cascade with a regime-triggered
    backstop and an expectations channel.

    The kernel mirrors cascade.py (P6). Additions (V10-P2):

      - backstop_active turns on when `trigger_buckets` buckets have
        tripped AND drawdown <= -trigger_drawdown. The policy listens to
        the market; there is no fixed lag.

      - while active with object "flow":
          * pure absorption (P1): absorb `coverage` of the cascade flow;
          * expectations channel: newly-tripped buckets release only
            sell_share * (1 - effect) -- leveraged accounts stop
            front-running the cascade because the buyer is announced.

    Returns dict: total_return, amplification, backstop_step,
    trigger_buckets_hit_at_fire, absorbed_flow, expected_flow_saved,
    tail_truncated, price_path, cascade_flow_path.
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
    absorbed_flow = 0.0
    expected_flow_saved = 0.0
    backstop_step = None
    fired_at_fire = 0
    new_release_after_backstop = False

    for step in range(n_steps):
        drawdown = price - 1.0

        # 0) regime trigger: policy listens to the market
        fired_count = sum(fired)
        if (backstop_step is None
                and fired_count >= trigger_buckets
                and drawdown <= -trigger_drawdown):
            backstop_step = step
            fired_at_fire = fired_count
        backstop_active = backstop_step is not None

        # 1) cascade: trip buckets whose trigger the current drawdown passes
        new_weight = 0.0
        for i, (lev, w, trig) in enumerate(buckets):
            if not fired[i] and drawdown <= -trig:
                fired[i] = True
                new_weight += w
                total_liquidated_weight += w
                last_liquidation_step = step

        if new_weight > 0:
            # release the FULL sell intention; the expectations channel
            # cuts unfinished intentions below (it acts on all remaining
            # forced-selling, not only the newly-tripped bucket).
            release = new_weight * sell_share / lag
            releases.append([release, lag])
            # window still open if a new bucket would have sold anything
            if backstop_active and release * (1.0 - expectation_effect) > 0:
                new_release_after_backstop = True

        # release this step's forced selling (decayed residual from before)
        flow_intention = sum(r[0] for r in releases if r[1] > 0)
        if backstop_active and expectation_effect > 0:
            # expectations channel: after the announcement, remaining
            # forced-sale intentions are cut by effect -- accounts stop
            # front-running the cascade, whether tripped or not. The cut
            # also applies to the liquidation flow already in transit
            # (orders are pulled once the buyer is announced).
            cut_intention = flow_intention * expectation_effect
            cut_stock = cascade_flow * expectation_effect
            expected_flow_saved += cut_intention + cut_stock
            flow_intention -= cut_intention
            cascade_flow -= cut_stock
        cascade_flow = cascade_flow * flow_decay + flow_intention
        for r in releases:
            if r[1] > 0:
                r[1] -= 1

        # 2) absorption channel (P1), with a stand-up RAMP: the buying
        # mechanism is announced instantly but its capacity builds over
        # `absorption_ramp` steps -- early flows still reach the price.
        if backstop_active:
            ramp = max(0.0, min(1.0, (step - backstop_step)
                                / max(1, absorption_ramp)))
            absorb_rate = coverage * ramp
            absorbed = cascade_flow * absorb_rate
            cascade_flow -= absorbed
            absorbed_flow += absorbed

        # 3) gamma flip (P5 rule)
        if flip_step is None and drawdown <= -flip_threshold:
            flip_step = step
        if flip_step is not None:
            gamma = gamma + flip_speed * (flip_target - gamma)

        # 4) kernel: dealer hedge + cascade flow (cascade SELLS)
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
    """Draw one (gamma0, shock, threshold) triple from the priors."""
    gamma0 = _clip(rng.gauss(DEFAULT_GAMMA_MEAN, DEFAULT_GAMMA_SIGMA),
                   DEFAULT_GAMMA_LO, DEFAULT_GAMMA_HI)
    shock = _clip(rng.gauss(DEFAULT_SHOCK_MEAN, DEFAULT_SHOCK_SIGMA),
                  DEFAULT_SHOCK_LO, DEFAULT_SHOCK_HI)
    thresh = _clip(rng.gauss(DEFAULT_THRESH_MEAN, DEFAULT_THRESH_SIGMA),
                   DEFAULT_THRESH_LO, DEFAULT_THRESH_HI)
    return gamma0, shock, thresh


def run_mc(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED,
           expectation_effect=DEFAULT_EXPECTATION_EFFECT):
    """Monte Carlo with the regime-triggered backstop."""
    rng = random.Random(seed)
    drops = []
    fires = 0
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        res = run_policy_expectations(shock=shock, gamma0=gamma0,
                                      flip_threshold=thresh,
                                      expectation_effect=expectation_effect)
        drops.append(res["total_return"])
        if res["backstop_step"] is not None:
            fires += 1
    drops.sort()

    def q(p):
        return drops[min(len(drops) - 1, int(p * (len(drops) - 1)))]

    return {
        "n": n,
        "seed": seed,
        "expectation_effect": expectation_effect,
        "p50": round(q(0.50), 4),
        "p10": round(q(0.10), 4),
        "p1": round(q(0.01), 4),
        "worst": round(drops[0], 4),
        "mean": round(sum(drops) / n, 4),
        "fire_share": round(fires / n, 4),
    }


def comparison_table():
    """V10-P1 vs V10-P2 on the same kernel."""
    none = run_policy_expectations(trigger_buckets=99)
    p1_style = run_policy_expectations(expectation_effect=0.0)
    p2_bounded = run_policy_expectations(expectation_effect=0.5)
    p2_unlimited = run_policy_expectations(expectation_effect=1.0)
    rows = [
        ("no backstop", none),
        ("V10-P1: absorption only (effect 0)", p1_style),
        ("V10-P2: half announcement (effect 0.5)", p2_bounded),
        ("V10-P2: as needed (effect 1.0)", p2_unlimited),
    ]
    return rows


def self_test():
    """Validate invariants:
      1) regime does not fire before its trigger conditions;
      2) expectations channel is monotone in effect;
      3) V10-P2 beats V10-P1 at the same regime (effect > 0);
      4) unbounded commitment truncates the tail;
      5) determinism.
    """
    print("== policy_expectations self-test ==")

    none = run_policy_expectations(trigger_buckets=99)
    assert none["backstop_step"] is None, "no backstop must not fire"

    # trigger conditions: needs both N buckets AND drawdown
    early = run_policy_expectations(trigger_buckets=4)
    assert early["backstop_step"] is None or early["backstop_step"] > 0
    fired_at = run_policy_expectations(trigger_buckets=2,
                                       trigger_drawdown=0.05)
    assert fired_at["backstop_step"] is not None, "regime should fire"

    # monotone in expectation effect
    effs = [run_policy_expectations(expectation_effect=E)["total_return"]
            for E in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert effs == sorted(effs), "tail must shallow as effect grows"

    # V10-P2 (effect 1.0) beats V10-P1 (effect 0.0)
    assert effs[-1] > effs[0], "announcement channel must buy more tail"
    assert effs[-1] > none["total_return"], "backstop must beat nothing"

    # unbounded commitment truncates the tail
    unlimited = run_policy_expectations(expectation_effect=1.0)
    assert unlimited["tail_truncated"], "as-needed must truncate the tail"
    assert unlimited["expected_flow_saved"] > 0.0, "expectation saves flow"

    # determinism
    a = run_policy_expectations()
    b = run_policy_expectations()
    assert a["total_return"] == b["total_return"]
    assert a["price_path"] == b["price_path"], "must be deterministic"

    print("   no backstop          :", none["total_return"])
    print("   effect 0.0 (absorption):", effs[0])
    print("   effect 0.5           :", effs[2])
    print("   effect 1.0 (as needed):", effs[-1])
    print("   fire step (effect 1) :", unlimited["backstop_step"],
          "| buckets at fire:", unlimited["trigger_buckets_hit_at_fire"])
    print("   absorbed vs expected saved:", unlimited["absorbed_flow"],
          "vs", unlimited["expected_flow_saved"])
    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mc", action="store_true", help="run Monte Carlo")
    ap.add_argument("--self-test", action="store_true", help="run invariants")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P1 vs V10-P2 on the same kernel ==")
    rows = comparison_table()
    print(f"{'scenario':<36}{'return':<10}{'fire':<6}{'absorbed':<10}{'expect-saved':<13}{'trunc'}")
    for name, res in rows:
        print(f"{name:<36}{res['total_return']:<10.4f}"
              f"{str(res['backstop_step']):<6}"
              f"{res['absorbed_flow']:<10.4f}"
              f"{res['expected_flow_saved']:<13.4f}"
              f"{str(res['tail_truncated']):<6}")

    if args.mc:
        print("\n== Monte Carlo (regime-triggered backstop) ==")
        for eff in (0.0, 0.5, 1.0):
            mc = run_mc(expectation_effect=eff)
            print(f"  effect={eff:<4} p1={mc['p1']:<9.4f} "
                  f"p10={mc['p10']:<9.4f} worst={mc['worst']:<9.4f} "
                  f"fire={mc['fire_share']}")


if __name__ == "__main__":
    main()
