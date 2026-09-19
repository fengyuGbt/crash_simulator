# The Backstop That Listens: Regime Triggers and the Expectations Channel

*Fat Tail Notes · Part 13 · V10-P2*

Part 12 built the backstop clock: `backstop = f(trigger, lag, coverage, object)`, calibrated on March 2020, and ended with an explicit debt. Two things the fixed-lag version could not do:

1. **The Fed does not arrive on a calendar.** It arrives when the regime is confirmed. On March 23, 2020, the flow tool fired not because it was "day 20" but because corporate-credit dysfunction had become unmistakable. A backstop with a hard-coded lag is a calendar; the real one is a *state machine*.
2. **A bounded number is a price tool in disguise.** "$700 billion" can be priced by the market, so panic is not removed — the cascade keeps front-running, and the backstop just absorbs the flow after it is born. The unbounded "as needed" commitment does something else entirely: it changes the *expectation* of the liquidation, so the liquidation never fully happens.

This article pays that debt. **V10-P2 (`policy_expectations.py`) makes the backstop endogenous — it listens to the market — and adds the expectations channel: after the announcement, forced-selling intentions are cut, including flow already in transit.** Same kernel as Parts 6–12. Two new mechanisms.

## 1. The regime trigger: the policy listens to the market

In V10-P1 the backstop activated at a fixed step. In V10-P2 it activates on *state*:

```
backstop fires  when  (buckets tripped >= trigger_buckets)
                    AND (drawdown <= -trigger_drawdown)
```

With the calibrated defaults — 2 tripped buckets and a 20% drawdown — the backstop fires at **step 14 of 40** on the March-2020 calibration path: the day the market has already given up 20% and two leverage cohorts have been liquidated. That is the "Mar 23" neighborhood, reached by listening, not by counting.

The asymmetry this creates is the point: **in a fast crash the endogenous trigger fires earlier than any fixed lag; in a slow grind it waits.** The policy does not need to predict the crisis — it needs to recognize it.

## 2. The expectations channel: cutting the intention, not just catching the flow

V10-P1's absorption channel waits for forced selling to be *born*, then buys it. That is expensive, lagged, and — as Part 12 showed — the price path is identical whether the backstop exists or not, because the selling still happens.

The expectations channel operates one step earlier. When the backstop activates with `expectation_effect = E`:

- **unfinished forced-sale intentions** are cut by a fraction E — accounts that would have kept dumping stop, because a buyer is announced;
- **liquidation flow already in transit** is also cut by E — orders get pulled once the buyer is known.

`E = 0` is the V10-P1 world: pure absorption, panic intact. `E = 1.0` is the unbounded "as needed" commitment: the *expectation of the liquidation* disappears, so the liquidation stops being born.

The accounting on the calibration path says it plainly:

| scenario | total return | absorbed flow | expected flow saved |
|---|---|---|---|
| no backstop | **-36.5%** | 0 | 0 |
| endogenous + absorption only (E = 0) | **-26.9%** | 0.188 | 0 |
| endogenous + half announcement (E = 0.5) | **-24.1%** | 0.043 | 0.213 |
| endogenous + as needed (E = 1.0) | **-22.8%** | 0 | 0.277 |

Read the last two columns. **At E = 1.0 the absorption channel is unemployed** — the expected-flow savings (0.277) exceed everything the buyer ever had to buy. The unbounded commitment does not work by buying; it works by *not having to buy*, because the selling it announces against never materializes.

## 3. The timing window: too late is just an absorber

The endogenous trigger introduces a knife's edge. Scan the trigger drawdown on the same path:

| trigger drawdown | fire step | E = 0 return | E = 1.0 return | gap |
|---|---|---|---|---|
| 10% | 4 | -16.7% | -15.0% | 1.7 pts |
| 20% | 14 | -26.9% | -22.8% | **4.1 pts** |
| 30% | 22 | -33.9% | -33.9% | **0.0 pts** |

At a 30% trigger the backstop fires so late that **every leverage bucket has already blown up** — there is no forced-selling intention left to cut, and the "as needed" commitment behaves exactly like a bounded one. A backstop that arrives after the cascade is finished is not a backstop; it is a souvenir.

This is the real lesson of the timing window: **the expectations channel has value only while there are still leveraged accounts that have not blown up.** The window is between "the regime is recognizable" and "the cascade has consumed everything." 2020's bottom happened because the announcement landed inside that window.

## 4. The distribution: the tail moves, not the body

Monte Carlo (2,000 paths, seed 20260919), regime-triggered backstop:

| expectation effect | p1 | p10 | worst | fire share |
|---|---|---|---|---|
| 0.0 (absorption only) | -30.0% | -28.5% | -32.9% | 91% |
| 0.5 | -26.2% | -24.9% | -29.5% | 91% |
| 1.0 (as needed) | **-24.4%** | **-23.2%** | **-27.7%** | 91% |

The expectations channel buys **5.6 points of p1 and 5.2 points of worst-case drawdown** — and it does so on 91% of paths, where the backstop fires. It is not a body-buyer; it is a **tail-buyer**. That is exactly what a policy residual is for.

## 5. What this means

Three claims, now with a kernel behind them:

1. **Endogenous beats calendar.** A backstop that listens to the market fires earlier in fast crashes and waits in slow ones. The Mar-2020 neighborhood is reached at step 14 by state recognition, not by counting to 20.
2. **The unbounded commitment is not a bigger check — it is a different mechanism.** A bounded number is priced, so panic survives and flow is born, then absorbed. An unbounded commitment cuts the intention before the flow is born. The absorption channel ends up with nothing to do (0.277 of expected flow saved vs 0 absorbed).
3. **Timing is everything, and it is a window, not a point.** Fire too early and you waste credibility; fire too late and you are an absorber with no expectations to repair. The value of the announcement is concentrated in the interval between "regime confirmed" and "cascade complete" — and 2020 bottomed because the announcement landed inside it.

Next iteration already has a candidate: **what happens when the market learns the rule** — when leveraged accounts know the trigger thresholds and front-run *the backstop itself*. That is the game of endogenous policy, and it deserves its own part.

---

*Code: `crash_simulator_v10/policy_expectations.py` (V10-P2), self-test and Monte Carlo included. Deterministic, 394 lines, no dependencies beyond the standard library.*

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

*本文由 AI 辅助撰写，经作者审阅。*
