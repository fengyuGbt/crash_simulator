# The Backstop Clock: Pricing the Twenty-Day Window in Code

Part 11 ended with a promise: stop treating the Fed as a residual and
make the policy explicit — `backstop = f(trigger_t, lag_t, coverage, object)`.
This is the module that delivers it. `policy_backstop.py` (V10-P1) races
the policy clock against the margin cascade, calibrated on the March 2020
calendar. The results are not subtle.

---

## The kernel

The engine mirrors the Part-10 cascade (spiral + gamma flip + margin
buckets) with one addition: a policy layer that arrives at step `lag_t`
and, if its object is `flow`, absorbs `coverage` of the forced-selling
flow every step before it hits the price.

```python
backstop_arrived = step >= backstop_lag
if backstop_arrived and backstop_object == "flow":
    absorbed = cascade_flow * coverage
    cascade_flow -= absorbed   # the flow never reaches the price
```

That is the whole policy. Three objects, one rule:

- `object = "price"` — rate cuts, treasury QE. **Nothing is absorbed.**
  The cascade keeps feeding itself.
- `object = "flow"` — buying the asset being liquidated, backstopping
  seller funding. **The forced-selling flow disappears.**
- `coverage = 1.0` — "as needed", the March 23 commitment with no ceiling.

## The March 2020 calibration, reproduced

The kernel is run at 40 steps with slow forced-selling release, so the
cascade is still feeding the market when the backstop arrives — as the
liquidation was in the third week of March 2020.

| Scenario | Object | Lag | Return | Tail truncated |
|---|---|---|---|---|
| No backstop | none | — | **-36.5%** | — |
| Mar 3 cut (price) | price | 12 | **-36.5%** | no |
| Mar 15 cut to zero (price) | price | 8 | **-36.5%** | no |
| **Mar 23 (flow, as needed)** | flow | 20 | **-30.0%** | **yes** |
| Flow backstop, lag 5 | flow | 5 | -14.8% | yes |
| Flow backstop, coverage 0.5 | flow | 20 | -31.0% | yes |

Read the first three rows carefully. **The price tools changed nothing.**
Not less damage — *nothing*. The rate cuts did not bind to the forced
selling, so the cascade ran to the same -36.5% in all three runs. That is
the March 15, 2020 failure mode, reproduced by a rule one line long.

The flow backstop, arriving at lag 20 (Mar 3 → Mar 23), cuts the tail to
-30.0% and **closes the liquidation window**: no new bucket trips after
arrival, and the forced flow is absorbed to zero. The market bottomed on
the day the object switched to flow — the kernel says the same.

## The window is a tail multiplier

Now vary the lag and watch the tail:

- **lag 5** → **-14.8%** (the backstop arrives while only two buckets
  have tripped; the cascade never gets going)
- **lag 12** → -20.7%
- **lag 20** → -30.0% (the March 2020 number: the window had been open
  three weeks)

Every day of lag is a slice of the tail. A model that prices the news
shock but not the window cannot see this curve at all — it has one
number for every policy, because the policy is a residual.

Coverage matters less but still matters: a bounded 50% backstop gives
-31.0% against -30.0% for the unlimited one. The "as needed" commitment
buys about a point in this kernel — but that understates it. The real
value of the unbounded commitment is not the absorbed flow, it is the
*expectation* of forced selling disappearing, which the kernel does not
yet model. (V10-P2 candidate.)

## Monte Carlo: the tail moves as a distribution

2,000 paths with uncertain shock / gamma / thresholds:

| Policy | p1 | p10 | worst | paths truncated |
|---|---|---|---|---|
| No backstop | -44.3% | -40.6% | -46.7% | 0% |
| Flow backstop, lag 20 | -42.7% | -38.4% | -45.3% | **86%** |
| Flow backstop, lag 5 | -26.4% | -20.9% | -30.3% | 43% |

The lag-20 backstop shaves the p1 tail by only 1.6 points — because in
most paths the cascade had already done most of its damage by day 20.
The lag-5 backstop shaves p1 by **18 points** and p10 by **20 points**.
The liquidation window is not a calendar detail; it is where the tail
lives.

## What this means for the VaR

1. **Price tools are an invariant in liquidation-driven falls.** If your
   model lets the rate cut reduce the tail, it is wrong in a way that
   flatters the outcome. The kernel reproduces March 2020 by treating
   price tools as what they are: orthogonal to forced selling.
2. **The backstop belongs in the hazard/loss layer, not the residual.**
   Four parameters, one rule, a calibration date. That is all it takes to
   stop treating the Fed as a residual.
3. **The honest output is a truncated distribution, not an adjusted
   number.** The tail ends at a named date — the day the flow tool
   arrived. The kernel gives you the date; the MC gives you the share of
   paths that make it there.

The next iteration is already visible: the backstop should be triggered
endogenously (regime detection, not a fixed lag), and the unbounded
commitment should act on expectations, not just flow. But the core
promise of Part 11 is now code: **a VaR that prices the twenty-day
window instead of pretending it does not exist.**

---

*This article was written with AI assistance and reviewed by the author.*

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*
