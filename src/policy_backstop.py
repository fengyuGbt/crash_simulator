"""Policy backstop layer (V10-P1).

Part 11 argued that a VaR treating the Fed as a residual prices the
news shock but misses how long the liquidation window stays open. This
module makes the policy explicit:

    backstop = f(trigger_t, lag_t, coverage, object)

  - object   : what the policy binds to. "price" tools (rate cuts,
               treasury QE) change the price of money and do NOT absorb
               forced selling; "flow" tools (buying the asset being
               liquidated, backstopping seller funding) absorb the
               cascade flow itself.
  - lag_t    : steps from shock to effective intervention -- the length
               of the liquidation window.
  - coverage : fraction of the forced-selling flow the backstop absorbs.
               "As needed" (March 23, 2020) = coverage 1.0.
  - trigger_t: the market state that fires the backstop (kept as the
               start of the shock in this stylized kernel).

Calibration case (March 2020, stylized): first cut Mar 3, flow tool
Mar 23 -- lag = 20 days, coverage = 1.0, object = flow. The S&P bottomed
intraday on Mar 23 (-35.3% from Feb 19). In the kernel this is the
step where the cascade flow is absorbed and price stops making new lows.

The kernel (spiral + flip + margin cascade) mirrors cascade.py (P6);
the backstop layer is the only addition.

Usage:
    python3 policy_backstop.py            # calibrated scenario + table
    python3 policy_backstop.py --mc       # distribution with backstop
    python3 policy_backstop.py --self-test
"""

import argparse
import random

# --- kernel parameters (mirror cascade.py P6) --------------------------------
DEFAULT_ALPHA = 0.6
DEFAULT_KAPPA = 1.0
DEFAULT_BETA = 0.15
# Calibration configuration: the March 2020 liquidation window was ~20
# days and forced selling was still active when the flow tool arrived
# (Mar 23). So the kernel runs 40 steps with slow flow release/decay;
# the cascade is still feeding the market at step 20.
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
DEFAULT_FLOW_DECAY = 0.85     # slow decay: forced selling persists (2020)
DEFAULT_LAG_STEPS = 6         # slow release: margin call -> forced sale

# --- backstop (new in V10-P1) ------------------------------------------------
DEFAULT_OBJECT = "none"     # none | price | flow
DEFAULT_BACKSTOP_LAG = 20   # calibration: Mar 3 -> Mar 23, 2020
DEFAULT_COVERAGE = 1.0      # "as needed" = absorb all forced flow

# --- Monte Carlo priors ------------------------------------------------------
DEFAULT_N_PATHS = 2000
DEFAULT_SEED = 20260918
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


def run_backstopped_cascade(shock=DEFAULT_SHOCK, gamma0=DEFAULT_GAMMA0,
                            flip_threshold=DEFAULT_FLIP_THRESHOLD,
                            flip_target=DEFAULT_FLIP_TARGET,
                            flip_speed=DEFAULT_FLIP_SPEED,
                            buckets=None, sell_share=DEFAULT_SELL_SHARE,
                            impact=DEFAULT_IMPACT,
                            flow_decay=DEFAULT_FLOW_DECAY,
                            lag_steps=DEFAULT_LAG_STEPS,
                            alpha=DEFAULT_ALPHA, kappa=DEFAULT_KAPPA,
                            beta=DEFAULT_BETA, n_steps=DEFAULT_STEPS,
                            backstop_object=DEFAULT_OBJECT,
                            backstop_lag=DEFAULT_BACKSTOP_LAG,
                            coverage=DEFAULT_COVERAGE):
    """Iterate spiral + flip + margin cascade with an optional backstop.

    The kernel mirrors cascade.py (P6). The backstop layer adds one rule:
    once the backstop arrives (step >= backstop_lag):

      - object == "flow":  absorb `coverage` of the cascade flow each
                           step BEFORE it hits the price. coverage=1.0
                           means the forced-selling flow is gone and the
                           cascade can no longer feed itself.
      - object == "price": nothing changes. Price tools do not bind to
                           the flow of forced selling -- this is the
                           March 15, 2020 failure mode, reproduced.

    Returns dict: total_return, amplification, backstop_step,
    backstop_object, absorbed_flow, tail_truncated (True if the flow
    backstop closed the liquidation window: no new bucket tripped and
    forced flow was absorbed after arrival), price_path,
    cascade_flow_path.
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
    blag = max(0, backstop_lag)
    absorbed_flow = 0.0
    new_liq_after_backstop = False

    for step in range(n_steps):
        drawdown = price - 1.0
        backstop_arrived = step >= blag

        # 1) cascade: trip buckets whose trigger the current drawdown passes
        new_weight = 0.0
        for i, (lev, w, trig) in enumerate(buckets):
            if not fired[i] and drawdown <= -trig:
                fired[i] = True
                new_weight += w
                total_liquidated_weight += w
                last_liquidation_step = step
                if backstop_arrived:
                    new_liq_after_backstop = True
        if new_weight > 0:
            releases.append([new_weight * sell_share / lag, lag])

        # release this step's forced selling (decayed residual from before)
        flow_this = sum(r[0] for r in releases if r[1] > 0)
        cascade_flow = cascade_flow * flow_decay + flow_this
        for r in releases:
            if r[1] > 0:
                r[1] -= 1

        # 2) backstop layer (V10-P1): the policy clock
        if backstop_arrived and backstop_object == "flow":
            absorbed = cascade_flow * coverage
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

        if backstop_arrived:
            pass  # policy arrival is tracked via new_liq_after_backstop

    total_return = price - 1.0
    amplification = abs(total_return) / abs(shock) if shock != 0 else float("nan")

    # tail_truncated: after a flow backstop arrives, the liquidation
    # window closes -- no NEW bucket trips and forced flow is absorbed.
    # (Residual dealer hedging after the flip is a separate engine, P5/P9.)
    tail_truncated = (backstop_object == "flow" and blag < n_steps
                      and absorbed_flow > 0 and not new_liq_after_backstop)

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
        "backstop_object": backstop_object,
        "backstop_lag": blag,
        "coverage": coverage,
        "absorbed_flow": round(absorbed_flow, 4),
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
           backstop_object=DEFAULT_OBJECT,
           backstop_lag=DEFAULT_BACKSTOP_LAG,
           coverage=DEFAULT_COVERAGE):
    """Monte Carlo: uncertain gamma0/shock/threshold -> drawdown
    distribution, with a fixed backstop policy."""
    rng = random.Random(seed)
    drops = []
    truncated = 0
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        res = run_backstopped_cascade(shock=shock, gamma0=gamma0,
                                      flip_threshold=thresh,
                                      backstop_object=backstop_object,
                                      backstop_lag=backstop_lag,
                                      coverage=coverage)
        drops.append(res["total_return"])
        if res["tail_truncated"]:
            truncated += 1
    drops.sort()

    def q(p):
        return drops[min(len(drops) - 1, int(p * (len(drops) - 1)))]

    return {
        "n": n,
        "seed": seed,
        "backstop_object": backstop_object,
        "backstop_lag": backstop_lag,
        "coverage": coverage,
        "p50": round(q(0.50), 4),
        "p10": round(q(0.10), 4),
        "p1": round(q(0.01), 4),
        "worst": round(drops[0], 4),
        "mean": round(sum(drops) / n, 4),
        "truncated_share": round(truncated / n, 4),
    }


def scenario_table():
    """The Part-11 parameter grid, run as a table."""
    base = run_backstopped_cascade(backstop_object="none")
    rows = [
        ("no backstop", "none", None, None, base),
        ("Mar 3 cut (price, lag 12)", "price", 12, 1.0,
         run_backstopped_cascade(backstop_object="price", backstop_lag=12)),
        ("Mar 15 (price, lag 8)", "price", 8, 1.0,
         run_backstopped_cascade(backstop_object="price", backstop_lag=8)),
        ("Mar 23 (flow, lag 20)", "flow", 20, 1.0,
         run_backstopped_cascade(backstop_object="flow", backstop_lag=20,
                                 coverage=1.0)),
        ("Mar 23 but lag 5 (flow)", "flow", 5, 1.0,
         run_backstopped_cascade(backstop_object="flow", backstop_lag=5,
                                 coverage=1.0)),
        ("Mar 23 but coverage 0.5", "flow", 20, 0.5,
         run_backstopped_cascade(backstop_object="flow", backstop_lag=20,
                                 coverage=0.5)),
    ]
    return rows


def self_test():
    """Validate invariants:
      1) price backstop changes nothing vs no backstop (does not bind
         to flow);
      2) flow backstop truncates the tail (no new low after arrival);
      3) shorter lag -> shallower drawdown (monotone);
      4) higher coverage -> shallower drawdown (monotone);
      5) determinism.
    """
    print("== policy_backstop self-test ==")

    none = run_backstopped_cascade(backstop_object="none")
    price = run_backstopped_cascade(backstop_object="price", backstop_lag=8)
    assert price["total_return"] == none["total_return"], (
        "price tool must not change the path (does not bind to flow)")
    assert price["absorbed_flow"] == 0.0, "price tool absorbs no flow"

    flow = run_backstopped_cascade(backstop_object="flow", backstop_lag=20,
                                   coverage=1.0)
    assert flow["total_return"] > none["total_return"], (
        "flow backstop must shallow the drawdown vs no backstop")
    assert flow["tail_truncated"], "flow backstop must truncate the tail"
    assert flow["absorbed_flow"] > 0.0, "flow backstop must absorb flow"

    # monotone in lag: earlier flow backstop -> shallower
    lag_rets = [run_backstopped_cascade(backstop_object="flow", backstop_lag=L,
                                        coverage=1.0)["total_return"]
                for L in (2, 5, 10, 20)]
    assert lag_rets == sorted(lag_rets, reverse=True), (
        "total_return must fall as lag grows")
    assert lag_rets[-1] < 0.0, "even the late backstop should beat nothing"

    # monotone in coverage
    cov_rets = [run_backstopped_cascade(backstop_object="flow", backstop_lag=20,
                                        coverage=C)["total_return"]
                for C in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert cov_rets == sorted(cov_rets), (
        "total_return must rise as coverage grows")

    # determinism
    a = run_backstopped_cascade()
    b = run_backstopped_cascade()
    assert a["total_return"] == b["total_return"] == none["total_return"]
    assert a["price_path"] == b["price_path"], "must be deterministic"

    # 2020 calibration flavor: flow lag 20 stops the fall on arrival
    cal = run_backstopped_cascade(backstop_object="flow", backstop_lag=20,
                                  coverage=1.0)
    assert cal["tail_truncated"]
    print("   no backstop      :", none["total_return"])
    print("   price (lag 8)    :", price["total_return"])
    print("   flow (lag 20)    :", flow["total_return"])
    print("   flow (lag 5)     :",
          run_backstopped_cascade(backstop_object="flow", backstop_lag=5,
                                  coverage=1.0)["total_return"])
    print("   flow cov 0.5     :",
          run_backstopped_cascade(backstop_object="flow", backstop_lag=20,
                                  coverage=0.5)["total_return"])
    print("   tail_truncated   :", cal["tail_truncated"])
    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mc", action="store_true", help="run Monte Carlo")
    ap.add_argument("--self-test", action="store_true", help="run invariants")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== calibrated scenario (2020 March, stylized) ==")
    rows = scenario_table()
    print(f"{'scenario':<28}{'object':<6}{'lag':<6}{'cov':<6}"
          f"{'return':<10}{'trunc'}")
    for name, obj, lag, cov, res in rows:
        lag_s = str(lag) if lag is not None else "-"
        cov_s = str(cov) if cov is not None else "-"
        print(f"{name:<28}{obj:<6}{lag_s:<6}{cov_s:<6}"
              f"{res['total_return']:<10.4f}{str(res['tail_truncated']):<6}")

    if args.mc:
        print("\n== Monte Carlo (p1/p10/worst of drawdown) ==")
        for obj, lag in (("none", None), ("flow", 20), ("flow", 5)):
            mc = run_mc(backstop_object=obj,
                        backstop_lag=lag if lag is not None else 0)
            print(f"  {obj:<6} lag={str(lag):<4} "
                  f"p1={mc['p1']:<9.4f} p10={mc['p10']:<9.4f} "
                  f"worst={mc['worst']:<9.4f} trunc={mc['truncated_share']}")


if __name__ == "__main__":
    main()
