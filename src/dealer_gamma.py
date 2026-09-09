"""Dealer gamma feedback loop (V9-P1).

Models the market-maker hedging spiral: when dealers are net short gamma, a
selloff forces mechanical delta-hedge selling, which pushes prices down
further, which forces more selling -- manufacturing the tail event.

This is a MECHANISM model, not a calibrated GEX model: full options-chain
position data (OCC) is not freely available, so net gamma exposure is
approximated from market state (VIX/SKEW). Parameters are configurable and
documented below. The point is the feedback structure, not point estimates.

Response to Dean Lee's feedback on Part 1:
    "When dealers are short gamma in a selloff, mechanical hedging forces
     them to sell into a falling market, manufacturing the tail event."

Usage:
    python3 dealer_gamma.py                 # -5% scenario with current market state
    python3 dealer_gamma.py --self-test     # validate mechanism invariants

Mechanism (per time step):
    hedge_flow_t = -kappa * net_gamma * ret_t     # delta-neutral rebalancing
    ret_{t+1}    =  alpha * ret_t + beta * hedge_flow_t
    multiplier   =  alpha - beta * kappa * net_gamma

    short gamma (net_gamma<0): falling price -> dealer SELLS -> deeper fall
    long  gamma (net_gamma>0): falling price -> dealer BUYS  -> fall damped
"""

import argparse

# Default feedback parameters (documented, configurable).
DEFAULT_ALPHA = 0.6      # natural shock decay per step
DEFAULT_KAPPA = 1.0      # hedge sensitivity to price move
DEFAULT_BETA = 0.15      # hedge-flow impact on price
DEFAULT_STEPS = 12       # simulation horizon
DEFAULT_SHOCK = -0.05    # initial exogenous shock (-5%)

# Optional intervention: when cumulative drop exceeds trigger_pct, inject
# positive flow for `steps` periods (central-bank / dealer rebalance style).
DEFAULT_INTERVENTION = {"trigger_pct": 0.06, "steps": 3, "size": 0.006}


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def estimate_net_gamma(state, skew_key="skew_pctile_5y", vix_key="vix_pctile_5y"):
    """Approximate net dealer gamma (-1..1) from market state.

    Negative = dealers short gamma (tail-protection demand high, i.e. high
    SKEW percentile -> they have sold volatility). Calm volatility with
    elevated SKEW is the classic short-gamma accumulation regime.
    """
    skew_pctile = state.get(skew_key)
    vix_pctile = state.get(vix_key)
    skew_pctile = 0.5 if skew_pctile is None else float(skew_pctile)
    vix_pctile = 0.5 if vix_pctile is None else float(vix_pctile)
    gamma = -(skew_pctile - 0.5) * 2.0            # skew 0.5 -> 0, 0.9 -> -0.8
    if skew_pctile >= 0.85 and vix_pctile < 0.80:
        gamma = min(gamma, -0.8)                  # calm + expensive protection
    return round(clip(gamma, -1.0, 1.0), 4)


def run_spiral(shock=DEFAULT_SHOCK, net_gamma=0.0, alpha=DEFAULT_ALPHA,
               kappa=DEFAULT_KAPPA, beta=DEFAULT_BETA, n_steps=DEFAULT_STEPS,
               intervention=None):
    """Iterate the dealer-hedging feedback loop.

    Returns dict: amplification (cumulative drop / |shock|), total_return,
    paths, peak hedge flow, and whether an intervention fired.
    """
    ret = shock
    price = 1.0
    price_path = [price]
    hedge_path = []
    cumulative = 0.0
    intervention_used = False
    active_intervention = 0

    for _ in range(n_steps):
        hedge_flow = -kappa * net_gamma * ret          # delta-neutral rebalance
        cumulative += ret
        if intervention is not None:
            if -cumulative >= intervention["trigger_pct"]:
                active_intervention = intervention["steps"]
                intervention_used = True
        if active_intervention > 0:
            hedge_flow += intervention["size"]
            active_intervention -= 1
        ret_next = alpha * ret + beta * hedge_flow
        hedge_path.append(round(hedge_flow, 6))
        price = price * (1.0 + ret)
        price_path.append(round(price, 6))
        ret = ret_next

    total_return = price - 1.0
    amplification = abs(total_return) / abs(shock) if shock != 0 else float("nan")
    return {
        "shock_size": shock,
        "net_gamma": net_gamma,
        "amplification": round(amplification, 3),
        "total_return": round(total_return, 4),
        "peak_hedge_flow": round(min(hedge_path), 6),
        "intervention_used": bool(intervention_used),
        "price_path": price_path,
        "hedge_flow_path": hedge_path,
    }


def classify(result, amp_no_gamma):
    """spiral / dampened / stabilized, relative to the no-gamma baseline."""
    amp = result["amplification"]
    if amp > amp_no_gamma * 1.1:
        return "spiral"
    if amp < amp_no_gamma * 0.9:
        return "stabilized"
    return "dampened"


def print_result(result, label=""):
    print(f"== dealer gamma scenario {label}==")
    for k in ("shock_size", "net_gamma", "amplification", "total_return",
              "peak_hedge_flow", "intervention_used"):
        print(f"  {k}: {result[k]}")


def run_scenario(net_gamma, intervention=None):
    return run_spiral(DEFAULT_SHOCK, net_gamma, intervention=intervention)


def self_test():
    """Validate mechanism invariants without network access."""
    print("== dealer_gamma self-test ==")
    base = run_spiral(DEFAULT_SHOCK, 0.0)                     # no gamma
    short = run_spiral(DEFAULT_SHOCK, -0.8)                   # short gamma
    long = run_spiral(DEFAULT_SHOCK, 0.8)                     # long gamma
    intervened = run_spiral(DEFAULT_SHOCK, -0.8,              # + intervention
                            intervention=dict(DEFAULT_INTERVENTION))

    assert short["amplification"] > base["amplification"], (
        f"short gamma must amplify: {short['amplification']} <= {base['amplification']}")
    assert long["amplification"] < base["amplification"], (
        f"long gamma must damp: {long['amplification']} >= {base['amplification']}")
    assert short["peak_hedge_flow"] < 0, (
        f"short gamma must sell into falls: {short['peak_hedge_flow']}")
    assert long["peak_hedge_flow"] > 0, (
        f"long gamma must buy into falls: {long['peak_hedge_flow']}")
    assert intervened["amplification"] < short["amplification"], (
        f"intervention must reduce amplification: {intervened['amplification']} >= {short['amplification']}")
    assert intervened["intervention_used"] is True, "intervention should fire"
    again = run_spiral(DEFAULT_SHOCK, -0.8)
    assert again["price_path"] == short["price_path"], "non-deterministic run"

    print(f"  no-gamma   amplification: {base['amplification']:>6.3f}")
    print(f"  short-gamma amplification: {short['amplification']:>6.3f}  (spiral)  peak hedge flow: {short['peak_hedge_flow']}")
    print(f"  long-gamma  amplification: {long['amplification']:>6.3f}  (damped)  peak hedge flow: {long['peak_hedge_flow']}")
    print(f"  short+interv amplification: {intervened['amplification']:>6.3f}  (intervention fired: {intervened['intervention_used']})")
    print("== self-test OK ==")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Dealer gamma feedback loop")
    parser.add_argument("--self-test", action="store_true",
                        help="validate mechanism invariants")
    parser.add_argument("--shock", type=float, default=DEFAULT_SHOCK,
                        help="initial exogenous shock (default -0.05)")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    try:
        import market_state
        state = market_state.compute_state()
    except Exception as exc:  # offline fallback: neutral market
        print(f"  [warn] market_state unavailable ({exc}); using neutral state")
        state = {"vix_pctile_5y": 0.5, "skew_pctile_5y": 0.5}

    net_gamma = estimate_net_gamma(state)
    print(f"== market state (from VIX/SKEW) ==")
    for k, v in state.items():
        print(f"  {k}: {v}")
    print(f"  -> estimated net dealer gamma: {net_gamma}")

    base = run_spiral(args.shock, 0.0)
    result = run_spiral(args.shock, net_gamma)
    regime = classify(result, base["amplification"])
    print_result(result, f"(shock {args.shock}, gamma {net_gamma}, regime: {regime})")
    print("  (relative to no-gamma baseline amplification "
          f"{base['amplification']})")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
