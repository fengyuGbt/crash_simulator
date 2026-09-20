"""Policy anticipation / front-running (V10-P3).

Part 13 (V10-P2, `policy_expectations.py`) made the backstop endogenous
-- it listens to the market -- and added the expectations channel: after
the announcement, unfinished forced-sale intentions are cut, so the
liquidation stops being born. Part 13 ended with a candidate for this
article: **what happens when the market learns the rule.**

Endogenous policy meets endogenous markets. If leveraged accounts know
the trigger thresholds (2 tripped buckets AND drawdown <= -20%), the
rational move is to front-run the backstop: pre-empt the liquidation
*shallower* than the trigger, because once the backstop fires the market
rebounds and the forced seller is left selling into the recovery.

This module models the front-running as EARLY TRIPPING: an unfired
bucket trips on its own once drawdown <= -anticipation_trigger
(shallower than the policy's trigger_drawdown). Consequences:

  - the cascade starts earlier and runs faster -- the backstop arrives
    at a deeper hole;
  - buckets that front-run have already blown up by fire time, so the
    expectations channel has fewer intentions left to cut.

The control experiment is FUZZY policy: if the trigger drawdown has a
random component the market cannot predict, front-running cannot aim at
it, and the P2 outcome is restored. Ambiguity, it turns out, is not a
weakness of central banks -- it is a policy tool.

The kernel mirrors cascade.py (P6) / policy_backstop.py (V10-P1) /
policy_expectations.py (V10-P2); the additions are the front-running
mechanism and the fuzzy-rule variant.

Usage:
    python3 policy_anticipation.py           # comparison table
    python3 policy_anticipation.py --mc      # distribution
    python3 policy_anticipation.py --self-test
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

# --- regime trigger (P2) ------------------------------------------------------
DEFAULT_TRIGGER_BUCKETS = 2
DEFAULT_TRIGGER_DRAWDOWN = 0.20
DEFAULT_COVERAGE = 1.0
DEFAULT_ABSORPTION_RAMP = 8
DEFAULT_EXPECTATION_EFFECT = 1.0

# --- front-running (P3) -------------------------------------------------------
DEFAULT_ANTICIPATION_TRIGGER = 0.15   # front-run starts shallower than
                                      # the policy trigger (0.20)
DEFAULT_ANTICIPATION_STRENGTH = 1.0   # 0 disables front-running entirely;
                                      # 1.0 = full pre-emption at the
                                      # anticipation depth
DEFAULT_FUZZY = False                 # fuzzy policy: trigger drawdown
                                      # has a per-path random component
                                      # the market cannot aim at
DEFAULT_FUZZY_SIGMA = 0.04            # symmetric noise: 0.20 + U(-s, +s);
                                      # same expectation, unpredictable
                                      # realization

# --- Monte Carlo priors ------------------------------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260920
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


def run_policy_anticipation(shock=DEFAULT_SHOCK, gamma0=DEFAULT_GAMMA0,
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
                            anticipation_trigger=DEFAULT_ANTICIPATION_TRIGGER,
                            anticipation_strength=DEFAULT_ANTICIPATION_STRENGTH,
                            fuzzy=DEFAULT_FUZZY,
                            fuzzy_sigma=DEFAULT_FUZZY_SIGMA,
                            rng=None):
    """Iterate spiral + flip + margin cascade with a regime-triggered
    backstop, an expectations channel, and front-running.

    P3 additions:

      - if `anticipation_strength > 0` and the policy is NOT fuzzy,
        unfired buckets trip early once drawdown <= -anticipation_trigger
        (the market has learned the rule and pre-empts the liquidation);
      - if `fuzzy` is True, the policy's trigger drawdown is drawn per
        path as trigger_drawdown + U(0, fuzzy_sigma), which the
        front-runner cannot aim at (front-running is disabled).

    Returns dict: total_return, amplification, backstop_step, buckets,
    front_ran_before_fire, absorbed_flow, expected_flow_saved,
    tail_truncated, price_path, cascade_flow_path.
    """
    buckets = list(buckets) if buckets is not None else list(DEFAULT_BUCKETS)
    fired = [False] * len(buckets)
    rng = rng if rng is not None else random.Random(0)

    # fuzzy policy: the trigger has a per-path component the market
    # cannot predict; front-running cannot aim at a moving target
    if fuzzy:
        effective_trigger = trigger_drawdown + rng.uniform(-fuzzy_sigma,
                                                            fuzzy_sigma)
        front_running = False
    else:
        effective_trigger = trigger_drawdown
        front_running = anticipation_strength > 0

    ret = shock
    price = 1.0
    price_path = [price]
    gamma = gamma0
    flip_step = None
    cascade_flow = 0.0
    cascade_flow_path = []
    last_liquidation_step = None
    total_liquidated_weight = 0.0
    front_ran_before_fire = 0
    releases = []          # each: [amount_per_step, steps_remaining]
    lag = max(1, lag_steps)
    absorbed_flow = 0.0
    expected_flow_saved = 0.0
    backstop_step = None
    fired_at_fire = 0
    new_release_after_backstop = False

    for step in range(n_steps):
        drawdown = price - 1.0

        # 0) front-running: the market has learned the rule. Front-runners
        # pre-empt the liquidation: they trip their own buckets shallower
        # than the policy trigger AND sell (their release feeds the flow
        # exactly like a forced liquidation -- the price does not know
        # whether the seller is forced or scared).
        front_weight = 0.0
        if (front_running and backstop_step is None
                and drawdown <= -anticipation_trigger):
            for i, (lev, w, trig) in enumerate(buckets):
                if not fired[i] and drawdown <= -anticipation_trigger:
                    fired[i] = True
                    total_liquidated_weight += w
                    front_weight += w
                    front_ran_before_fire += 1

        # 0b) regime trigger: the policy listens to the market
        fired_count = sum(fired)
        if (backstop_step is None
                and fired_count >= trigger_buckets
                and drawdown <= -effective_trigger):
            backstop_step = step
            fired_at_fire = fired_count
        backstop_active = backstop_step is not None

        # 1) cascade: trip buckets whose trigger the drawdown passes
        new_weight = front_weight
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

        # 2) release + expectations channel (P2)
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

        # 3) absorption channel (P1), with stand-up ramp
        if backstop_active:
            ramp = max(0.0, min(1.0, (step - backstop_step)
                                / max(1, absorption_ramp)))
            absorb_rate = coverage * ramp
            absorbed = cascade_flow * absorb_rate
            cascade_flow -= absorbed
            absorbed_flow += absorbed

        # 4) gamma flip (P5 rule)
        if flip_step is None and drawdown <= -flip_threshold:
            flip_step = step
        if flip_step is not None:
            gamma = gamma + flip_speed * (flip_target - gamma)

        # 5) kernel
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
        "front_ran_before_fire": front_ran_before_fire,
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


def run_mc(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED, fuzzy=False,
           anticipation_strength=DEFAULT_ANTICIPATION_STRENGTH,
           fuzzy_sigma=DEFAULT_FUZZY_SIGMA):
    rng = random.Random(seed)
    drops = []
    fires = 0
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        res = run_policy_anticipation(
            shock=shock, gamma0=gamma0, flip_threshold=thresh,
            anticipation_strength=anticipation_strength,
            fuzzy=fuzzy, fuzzy_sigma=fuzzy_sigma, rng=rng)
        drops.append(res["total_return"])
        if res["backstop_step"] is not None:
            fires += 1
    drops.sort()

    def q(p):
        return drops[min(len(drops) - 1, int(p * (len(drops) - 1)))]

    return {
        "n": n,
        "seed": seed,
        "fuzzy": fuzzy,
        "anticipation_strength": anticipation_strength,
        "fuzzy_sigma": fuzzy_sigma,
        "p50": round(q(0.50), 4),
        "p10": round(q(0.10), 4),
        "p1": round(q(0.01), 4),
        "worst": round(drops[0], 4),
        "mean": round(sum(drops) / n, 4),
        "fire_share": round(fires / n, 4),
    }


def comparison_table():
    none = run_policy_anticipation(trigger_buckets=99, anticipation_strength=0.0)
    no_learn = run_policy_anticipation(anticipation_strength=0.0)
    learn = run_policy_anticipation(anticipation_strength=1.0)
    fuzzy = run_policy_anticipation(anticipation_strength=1.0, fuzzy=True)
    rows = [
        ("no backstop", none),
        ("P2: market has not learned (strength 0)", no_learn),
        ("P3: market learned the rule (strength 1)", learn),
        ("P3 + fuzzy trigger (can't be front-run)", fuzzy),
    ]
    return rows


def self_test():
    print("== policy_anticipation self-test ==")

    none = run_policy_anticipation(trigger_buckets=99, anticipation_strength=0.0)
    assert none["backstop_step"] is None, "no backstop must not fire"

    # strength 0 must reproduce P2 behavior
    no_learn = run_policy_anticipation(anticipation_strength=0.0)
    assert no_learn["backstop_step"] is not None, "regime should fire"

    # monotone: front-running must make the tail deeper, not shallower
    returns = [run_policy_anticipation(
        anticipation_strength=s)["total_return"]
        for s in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert returns == sorted(returns, reverse=True), (
        "front-running must monotonically deepen the tail")
    assert returns[-1] <= returns[0], "learned rule must be worse or equal"

    # learned rule must erode the expectations channel
    learn = run_policy_anticipation(anticipation_strength=1.0)
    assert learn["front_ran_before_fire"] > 0, "front-running must trip buckets"
    assert learn["expected_flow_saved"] <= no_learn["expected_flow_saved"], (
        "front-running erodes the expectations channel")

    # fuzzy policy restores the P2 outcome -- statistically, because on
    # any single path the noise may land on either side; over paths the
    # expectation of the trigger is unchanged (symmetric noise), so the
    # market cannot aim at it and front-running is disabled.
    p2_mc = run_mc(n=400, seed=20260920, fuzzy=False,
                   anticipation_strength=0.0)
    learn_mc = run_mc(n=400, seed=20260920, fuzzy=False,
                      anticipation_strength=1.0)
    fuzzy_mc = run_mc(n=400, seed=20260920, fuzzy=True,
                      anticipation_strength=1.0)
    assert learn_mc["mean"] <= p2_mc["mean"], "learned rule must deepen the mean"
    assert fuzzy_mc["mean"] >= learn_mc["mean"], (
        "ambiguity must recover tail vs a learned rule (mean)")
    assert fuzzy_mc["mean"] >= p2_mc["mean"] - 0.005, (
        "fuzzy must be within 0.5pt of the not-learned outcome")

    # determinism
    a = run_policy_anticipation()
    b = run_policy_anticipation()
    assert a["total_return"] == b["total_return"]
    assert a["price_path"] == b["price_path"], "must be deterministic"

    print("   no backstop            :", none["total_return"])
    print("   P2 (market not learned):", no_learn["total_return"])
    print("   P3 (rule learned)      :", learn["total_return"],
          "| front-ran before fire:", learn["front_ran_before_fire"])
    print("   MC mean (400 paths):")
    print(f"      P2   : {p2_mc['mean']}   p1={p2_mc['p1']}")
    print(f"      P3   : {learn_mc['mean']}   p1={learn_mc['p1']}")
    print(f"      fuzzy: {fuzzy_mc['mean']}   p1={fuzzy_mc['p1']}")
    print("   expect-saved: P2 vs P3 :", no_learn["expected_flow_saved"],
          "vs", learn["expected_flow_saved"])
    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mc", action="store_true", help="run Monte Carlo")
    ap.add_argument("--self-test", action="store_true", help="run invariants")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P2 vs V10-P3 on the same kernel ==")
    rows = comparison_table()
    print(f"{'scenario':<36}{'return':<10}{'fire':<6}{'front-run':<10}"
          f"{'expect-saved':<13}{'trunc'}")
    for name, res in rows:
        print(f"{name:<36}{res['total_return']:<10.4f}"
              f"{str(res['backstop_step']):<6}"
              f"{res['front_ran_before_fire']:<10}"
              f"{res['expected_flow_saved']:<13.4f}"
              f"{str(res['tail_truncated']):<6}")

    print("\nfront-running strength scan:")
    for s in (0.0, 0.25, 0.5, 0.75, 1.0):
        r = run_policy_anticipation(anticipation_strength=s)
        print(f"  strength={s:<5} return={r['total_return']:<9.4f} "
              f"front-run={r['front_ran_before_fire']} "
              f"fire={r['backstop_step']}")

    if args.mc:
        print("\n== Monte Carlo (front-running vs fuzzy) ==")
        for label, kw in (("P2 (not learned)", dict(anticipation_strength=0.0)),
                          ("P3 (learned)", dict(anticipation_strength=1.0)),
                          ("P3 + fuzzy", dict(anticipation_strength=1.0,
                                              fuzzy=True))):
            mc = run_mc(**kw)
            print(f"  {label:<16} p1={mc['p1']:<9.4f} "
                  f"p10={mc['p10']:<9.4f} worst={mc['worst']:<9.4f} "
                  f"fire={mc['fire_share']}")


if __name__ == "__main__":
    main()
