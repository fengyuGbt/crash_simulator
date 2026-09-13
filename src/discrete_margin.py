"""Discrete margin & threshold bunching (V9-P3).

Response to Dean Lee's comment on Part 4:
    "Forced selling is not a continuous ODE. Brokers mark at discrete
     intervals, and the next threshold often sits on a round number that
     a lot of accounts share. That bunching is why a 10 percent print can
     skip 12 and land at 18 before anyone has time to add cash."

What this module adds vs. system_dynamics.py (the continuous ODE version):

1. DISCRETE marking        - margin is checked every `mark_interval` steps,
                             not continuously.
2. THRESHOLD BUNCHING      - accounts cluster on round numbers (-10%, -15%,
                             -20%, ...). When price crosses a shared level,
                             a BATCH of accounts is liquidated at once,
                             so selling arrives in STEPS, not a slope.
3. LIQUIDATION WINDOW      - how long the forced-selling flow stays open
                             (first to last liquidation), and how much
                             cumulative flow it dumps - the part a VaR that
                             treats the Fed as a residual never prices.

The comparison object is the ODE-style release (what system_dynamics does):
selling pressure is a smooth function of how far price sits below each
threshold. Same thresholds, same book - one arrives in steps, one in a slope.

This is a MECHANISM model: parameters are documented, configurable and
chosen to exhibit the structure Dean describes, not calibrated to any
single crash. The point is the shape of the feedback, not point estimates.

Usage:
    python3 discrete_margin.py                 # discrete vs ODE demo
    python3 discrete_margin.py --self-test     # validate mechanism invariants
"""

import argparse

# Default mechanism parameters (documented, configurable).
DEFAULT_SHOCK = -0.15          # initial exogenous print (-15%)
DEFAULT_MARK_INTERVAL = 3      # margin checked every 3 steps (discrete)
DEFAULT_FORCED_SELL_RATIO = 0.30   # share of a bucket's book liquidated
DEFAULT_FLOW_IMPACT = 0.50     # price jump per unit of batch selling (thin book)
DEFAULT_RESIDUAL_IMPACT = 0.15 # residual-flow pressure on price (normal book)
DEFAULT_FLOW_DECAY = 0.45      # residual selling decays per step
DEFAULT_RECOVERY = 0.02        # mean reversion toward 1.0 per step
DEFAULT_STEPS = 40             # simulation horizon

# Integer-level clustered thresholds: (-level, fraction of accounts).
# Round numbers shared by many accounts - the "bunching" Dean describes.
CLUSTERED_BUCKETS = [
    (0.90, 0.25),   # -10%  triggers 25% of accounts
    (0.85, 0.30),   # -15%  triggers 30%
    (0.80, 0.25),   # -20%  triggers 25%
    (0.75, 0.20),   # -25%  triggers 20%
]

# Optional backstop: from `trigger_step` onward, absorb `flow` of selling per
# step (2020-style: cut the flow of forced sales, not the news).
DEFAULT_INTERVENTION = {"trigger_step": 5, "flow": 0.12}


class MarginBucket:
    """One cluster of accounts sharing the same margin threshold."""

    def __init__(self, threshold: float, share: float):
        self.threshold = threshold
        self.share = share
        self.liquidated = False

    def __repr__(self):  # pragma: no cover - debug aid
        return (f"MarginBucket(threshold={self.threshold:.3f}, "
                f"share={self.share:.3f}, liquidated={self.liquidated})")


class LiquidationEvent:
    """A liquidation: one shared threshold, one synchronous dump (discrete)."""

    def __init__(self, step: int, threshold: float, batch_share: float,
                 sell_flow: float, price_after: float):
        self.step = step
        self.threshold = threshold
        self.batch_share = batch_share
        self.sell_flow = sell_flow
        self.price_after = price_after

    def __repr__(self):  # pragma: no cover - debug aid
        return (f"LiquidationEvent(step={self.step}, threshold={self.threshold:.3f}, "
                f"batch={self.batch_share:.3f}, flow={self.sell_flow:.4f}, "
                f"price_after={self.price_after:.4f})")


def _make_buckets():
    """Build the clustered (integer-threshold) bucket set."""
    return [MarginBucket(t, s) for t, s in CLUSTERED_BUCKETS]


def _apply_intervention(sell_flow, intervention, step):
    """Backstop: absorb part of the forced-selling FLOW each step (2020-style)."""
    if intervention is not None and step >= intervention["trigger_step"]:
        return max(0.0, sell_flow - intervention["flow"])
    return sell_flow


def run_discrete(intervention: dict = None) -> dict:
    """Discrete marking + threshold bunching (the V9-P3 mechanism).

    - Margin is checked every `mark_interval` steps.
    - When price crosses a shared round threshold, the whole bucket is
      liquidated at once; the batch dump jumps the price, which can cross
      the next threshold within the same mark round ("skip 12, land at 18").
    """
    price = 1.0 * (1.0 + DEFAULT_SHOCK)
    sell_flow = 0.0
    buckets = _make_buckets()

    price_path = [round(price, 6)]
    flow_path = []
    events = []
    first_liq = None
    last_liq = None
    total_flow = 0.0

    for step in range(1, DEFAULT_STEPS + 1):
        # --- discrete marking -------------------------------------------------
        if step % DEFAULT_MARK_INTERVAL == 0:
            while True:
                hit = None
                for b in buckets:
                    if not b.liquidated and price <= b.threshold:
                        hit = b
                        break
                if hit is None:
                    break
                hit.liquidated = True
                flow = hit.share * DEFAULT_FORCED_SELL_RATIO
                sell_flow += flow
                total_flow += flow
                price = price * (1.0 - DEFAULT_FLOW_IMPACT * flow)  # thin book
                events.append(LiquidationEvent(
                    step, hit.threshold, hit.share, round(flow, 6),
                    round(price, 6)))
                if first_liq is None:
                    first_liq = step
                last_liq = step

        # --- backstop: cut the forced-selling FLOW ----------------------------
        sell_flow = _apply_intervention(sell_flow, intervention, step)

        # --- price evolution: mean reversion + residual selling ---------------
        natural = DEFAULT_RECOVERY * (1.0 - price)
        pressure = -DEFAULT_RESIDUAL_IMPACT * sell_flow * price
        price = price + natural + pressure
        price_path.append(round(price, 6))
        flow_path.append(round(sell_flow, 6))
        total_flow += sell_flow          # flow actually passing through market
        sell_flow *= DEFAULT_FLOW_DECAY

    max_drop = min(price_path) - 1.0
    window_steps = (last_liq - first_liq) if last_liq is not None else 0
    max_step_jump = max((price_path[i - 1] - price_path[i]
                         for i in range(1, len(price_path))), default=0.0)

    return {
        "model": "discrete",
        "max_drop": round(max_drop, 4),
        "final_price": round(price_path[-1], 4),
        "liquidation_events": len(events),
        "liquidation_window_steps": int(window_steps),
        "cumulative_sell_flow": round(total_flow, 4),
        "max_step_jump": round(max_step_jump, 6),
        "first_liquidation": first_liq,
        "last_liquidation": last_liq,
        "price_path": price_path,
        "events": events,
    }


def run_ode_style(intervention: dict = None) -> dict:
    """ODE-style release (what system_dynamics.py assumes): selling pressure
    is a smooth function of how far price sits below each threshold; no
    discrete marks, no batch jumps. Same thresholds, same book."""
    price = 1.0 * (1.0 + DEFAULT_SHOCK)
    sell_flow = 0.0
    buckets = _make_buckets()

    price_path = [round(price, 6)]
    flow_path = []
    events = []
    total_flow = 0.0

    for step in range(1, DEFAULT_STEPS + 1):
        # smooth activation: a bucket that breaches its threshold releases
        # flow proportional to the gap ONCE (its book is then gone), no batch
        # jump - the continuous-ODE assumption
        activated = 0
        for b in buckets:
            if not b.liquidated and price <= b.threshold:
                b.liquidated = True
                gap = max(0.0, (b.threshold - price) / b.threshold)
                piece = b.share * DEFAULT_FORCED_SELL_RATIO * (0.30 + 0.70 * gap)
                sell_flow += piece
                total_flow += piece
                activated += 1
        if activated:
            events.append(LiquidationEvent(step, 0.0, 0.0,
                                           round(activated * 0.0001, 6),
                                           round(price, 6)))

        sell_flow = _apply_intervention(sell_flow, intervention, step)

        natural = DEFAULT_RECOVERY * (1.0 - price)
        pressure = -DEFAULT_RESIDUAL_IMPACT * sell_flow * price
        price = price + natural + pressure
        price_path.append(round(price, 6))
        flow_path.append(round(sell_flow, 6))
        total_flow += sell_flow          # flow actually passing through market
        sell_flow *= DEFAULT_FLOW_DECAY

    max_drop = min(price_path) - 1.0
    max_step_jump = max((price_path[i - 1] - price_path[i]
                         for i in range(1, len(price_path))), default=0.0)

    return {
        "model": "ode",
        "max_drop": round(max_drop, 4),
        "liquidation_events": len(events),
        "liquidation_window_steps": len(events),
        "cumulative_sell_flow": round(total_flow, 4),
        "max_step_jump": round(max_step_jump, 6),
        "first_liquidation": events[0].step if events else None,
        "last_liquidation": events[-1].step if events else None,
        "price_path": price_path,
        "events": events,
    }


def compare_discrete_vs_ode(intervention: dict = None) -> dict:
    """Same thresholds, same book: discrete-batch vs ODE-smooth release."""
    discrete = run_discrete(intervention=intervention)
    ode = run_ode_style(intervention=intervention)
    conc_d = (discrete["max_step_jump"] / abs(discrete["max_drop"])
              if discrete["max_drop"] else 0.0)
    conc_o = (ode["max_step_jump"] / abs(ode["max_drop"])
              if ode["max_drop"] else 0.0)
    return {
        "discrete": discrete,
        "ode": ode,
        "steps_not_slope": bool(
            discrete["max_step_jump"] > ode["max_step_jump"]),
        "loss_concentration": (round(conc_d, 3), round(conc_o, 3)),
        "batched": bool(conc_d > conc_o),
    }


def print_run(result: dict, label: str = ""):
    print(f"== {result['model']} margin {label}==")
    for k in ("max_drop", "liquidation_events", "liquidation_window_steps",
              "cumulative_sell_flow", "max_step_jump"):
        print(f"  {k}: {result[k]}")
    if result["model"] == "discrete" and result["events"]:
        print("  liquidation timeline (step, threshold, batch, flow, price):")
        for e in result["events"]:
            print(f"    {e.step:>2}  {e.threshold:.2f}  {e.batch_share:.2f}  "
                  f"{e.sell_flow:.4f}  {e.price_after:.4f}")


def self_test() -> int:
    """Validate mechanism invariants (deterministic, no randomness)."""
    print("== discrete_margin self-test ==")

    # 1. small shock, no threshold crossed -> no liquidation, no crash
    small = _run_custom(-0.02)
    assert small["liquidation_events"] == 0, (
        f"small shock must not liquidate: {small['liquidation_events']}")
    assert small["max_drop"] > -0.10, (
        f"small shock must not crash: {small['max_drop']}")

    # 2. liquidation arrives as STEPS (batch jumps), not a smooth slope
    cmp = compare_discrete_vs_ode()
    assert cmp["steps_not_slope"], (
        f"discrete must step up: {cmp['discrete']['max_step_jump']} <= "
        f"{cmp['ode']['max_step_jump']}")

    # 3. selling is BATCHED: the loss is concentrated in few big steps,
    #    not spread across a smooth slope (concentration = jump / total drop)
    conc_d = (cmp["discrete"]["max_step_jump"] / abs(cmp["discrete"]["max_drop"])
              if cmp["discrete"]["max_drop"] else 0.0)
    conc_o = (cmp["ode"]["max_step_jump"] / abs(cmp["ode"]["max_drop"])
              if cmp["ode"]["max_drop"] else 0.0)
    assert conc_d > conc_o, (
        f"discrete must concentrate losses in steps: {conc_d:.3f} <= {conc_o:.3f}")

    # 4. liquidation window is measurable (discrete)
    assert cmp["discrete"]["liquidation_window_steps"] >= DEFAULT_MARK_INTERVAL, (
        f"window must be measurable: "
        f"{cmp['discrete']['liquidation_window_steps']}")

    # 5. determinism: same inputs -> same path
    again = run_discrete()
    assert again["price_path"] == cmp["discrete"]["price_path"], (
        "run must be deterministic")

    # 6. backstop intervention cuts the FLOW -> shallower drop, smaller flow,
    #    and a faster recovery (higher terminal price)
    inter = run_discrete(intervention=dict(DEFAULT_INTERVENTION))
    assert inter["max_drop"] > cmp["discrete"]["max_drop"], (
        f"intervention must shallow the drop: "
        f"{inter['max_drop']} <= {cmp['discrete']['max_drop']}")
    assert inter["cumulative_sell_flow"] < cmp["discrete"]["cumulative_sell_flow"], (
        f"intervention must cut the flow: "
        f"{inter['cumulative_sell_flow']} >= "
        f"{cmp['discrete']['cumulative_sell_flow']}")
    assert inter["final_price"] > cmp["discrete"]["final_price"], (
        f"intervention must speed recovery: "
        f"{inter['final_price']} <= {cmp['discrete']['final_price']}")

    print(f"  no-crash small shock       : events=0, max_drop={small['max_drop']}")
    print(f"  max step jump              : discrete {cmp['discrete']['max_step_jump']:.4f}"
          f" vs ode {cmp['ode']['max_step_jump']:.4f}"
          f"  (steps: {cmp['steps_not_slope']})")
    print(f"  loss concentration         : discrete {conc_d:.3f} vs ode {conc_o:.3f}"
          f"  (batched: {conc_d > conc_o})")
    print(f"  max drop (observation)     : discrete {cmp['discrete']['max_drop']}"
          f" vs ode {cmp['ode']['max_drop']}")
    print(f"  liquidation window         : {cmp['discrete']['liquidation_window_steps']} steps,"
          f" cumulative flow {cmp['discrete']['cumulative_sell_flow']}")
    print(f"  backstop intervention      : max_drop "
          f"{cmp['discrete']['max_drop']} -> {inter['max_drop']}, "
          f"flow {cmp['discrete']['cumulative_sell_flow']} -> "
          f"{inter['cumulative_sell_flow']}, "
          f"terminal price {cmp['discrete']['final_price']} -> {inter['final_price']}")
    print("== self-test OK ==")
    return 0


def _run_custom(shock: float) -> dict:
    """Internal discrete run with a custom shock (keeps module state clean)."""
    price = 1.0 * (1.0 + shock)
    sell_flow = 0.0
    buckets = _make_buckets()
    price_path = [round(price, 6)]
    events = []
    total_flow = 0.0
    for step in range(1, DEFAULT_STEPS + 1):
        if step % DEFAULT_MARK_INTERVAL == 0:
            while True:
                hit = None
                for b in buckets:
                    if not b.liquidated and price <= b.threshold:
                        hit = b
                        break
                if hit is None:
                    break
                hit.liquidated = True
                flow = hit.share * DEFAULT_FORCED_SELL_RATIO
                sell_flow += flow
                total_flow += flow
                price = price * (1.0 - DEFAULT_FLOW_IMPACT * flow)
                events.append(LiquidationEvent(step, hit.threshold, hit.share,
                                               round(flow, 6), round(price, 6)))
        natural = DEFAULT_RECOVERY * (1.0 - price)
        pressure = -DEFAULT_RESIDUAL_IMPACT * sell_flow * price
        price = price + natural + pressure
        price_path.append(round(price, 6))
        total_flow += sell_flow          # flow actually passing through market
        sell_flow *= DEFAULT_FLOW_DECAY
    max_drop = min(price_path) - 1.0
    return {
        "max_drop": round(max_drop, 4),
        "liquidation_events": len(events),
        "cumulative_sell_flow": round(total_flow, 4),
        "price_path": price_path,
        "events": events,
    }


def main() -> int:
    """CLI: --self-test validates; otherwise print the discrete/ODE demo."""
    if "--self-test" in __import__("sys").argv:
        return self_test()
    cmp = compare_discrete_vs_ode()
    print_run(cmp["discrete"], "(discrete marking + integer thresholds)")
    print_run(cmp["ode"], "(ODE-style smooth release)")
    print(f"\nDiscrete arrives in STEPS (max jump > ODE): {cmp['steps_not_slope']}")
    print(f"Discrete BATCHES the selling (loss concentration "
          f"{cmp['loss_concentration'][0]:.3f} vs "
          f"{cmp['loss_concentration'][1]:.3f}): {cmp['batched']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
