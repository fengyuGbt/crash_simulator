# The Twenty-Day Window: Pricing the Policy Residual

*A reader who works in derivatives — Dean Lee — wrote this about my Part 7, and it has been nagging me since:*

> "A VaR that treats the Fed as a residual still prices the news shock and misses how long that liquidation window stays open."

He is right, and 2020 is the proof. This article prices the window.

---

## The policy calendar that priced the tail

Between February 19 and March 23, 2020, the S&P 500 fell from 3,386 to 2,191 — **-35.3%**. The Fed did not stand still. It fired three times. The market bottomed exactly on the third shot:

| Date | Policy | Object | Market reaction |
|---|---|---|---|
| Mar 3 | Emergency cut, **-50bp** | Price of money | S&P **-2.8%** that day; sold off anyway |
| Mar 15 (Sun) | Emergency cut **-100bp** to zero + **$700B QE** | Price of money | Mar 16: **circuit breaker**, VIX closes at **82.69** (record) |
| Mar 23 | "**As needed**" purchases + corporate credit facilities (PMCCF/SMCCF) | **Flow of forced selling** | **Intraday low 2,191.86 that day — the exact bottom** |

Two of the three policies did not just fail to stop the crash — the second one *accelerated* it. The day after the biggest rate cut in Fed history, the market fell 12% and tripped its third circuit breaker in a week.

A VaR that treats the Fed as a residual books the shock correctly and then draws the wrong tail, because the tail was not set by the news. It was set by **how long the liquidation window stayed open** — twenty days, from first cut to effective backstop.

## Price tools vs flow tools

The distinction that matters is not "stimulus vs no stimulus." It is what the policy **binds to**:

- **Price tools** (rate cuts, treasury QE) change the *price of money*. They do not change the *flow* of forced selling. Leveraged accounts still get margin calls at the same thresholds; dealers still short gamma hedge on the next downtick.
- **Flow tools** (buying the asset class being liquidated, backstopping the sellers' funding) absorb or redirect the *selling flow itself*. The cascade loses its fuel.

March 15 was a price tool aimed at a flow problem. The market read it correctly: *"they are scared enough to cut 100bp on a Sunday — what do they know?"* The circuit breaker on March 16 was not a paradox. It was the price tool re-pricing the probability that the flow tool would arrive late.

March 23 was a flow tool. "As needed," "in the amounts needed to support smooth functioning" — the Fed did not announce a number, it announced that **it would absorb whatever flow the liquidation produced**. The bottom printed the same day.

## Backstop as a function of four parameters

Here is how I now think a stress-test model should hold the policy, instead of a residual:

```
backstop = f(trigger_t, lag_t, coverage, object)
```

- **object** ∈ {price, flow} — what the policy binds to (the one that decides everything)
- **lag_t** — days from shock to effective intervention (the length of the liquidation window)
- **coverage** — how much of the forced-selling flow the backstop absorbs
- **trigger_t** — the market state that fires it

The cascade module I built in Part 10 races margin cascades against the gamma flip. Add a backstop and the race has a third runner: the policy clock. The mechanisms stay the same — threshold clustering (Part 7), dealer hedging flow (Part 5), cascade buckets (Part 10) — but every one of them now has a **stop condition with a date on it**.

The 2020 data maps cleanly onto the parameter grid:

| Parameter | Mar 3 | Mar 15 | Mar 23 |
|---|---|---|---|
| object | price | price | **flow** |
| lag_t | 12 days before bottom | 8 days before bottom | **0 days before bottom** |
| coverage | n/a (does not bind to selling) | n/a | **"as needed" = ∞** |
| outcome | cascade continues | cascade accelerates | **cascade stops, same day** |

The window closed the day the object switched to flow. Everything before that — 3,000 points of drawdown, three circuit breakers, a record VIX — was the cost of a **price tool aimed at a flow problem**, measured in days.

## What the window does to the tail

This is the part the residual treatment loses. The liquidation window is not a calendar detail; it is a **tail multiplier**:

- While the window is open, margin cascades run their full course: every bucket fires on schedule, dealer hedging keeps selling into the fall, and the EP curve's deep tail gets populated.
- When a flow backstop arrives, the cascade stops mid-cycle. The forced-selling flow that would have cleared buckets 3 and 4 is absorbed instead. The realized tail is **truncated at the intervention date**, not at the fundamental fair value.

A model that prices the news shock but not the window therefore has a systematic bias: it over-prices tail events in markets where flow backstops exist (large, central-bank-backed equity markets), and under-prices them where they do not (crypto, single-name margin books, anything without a lender of last resort for its sellers).

The sign of the bias depends entirely on the object — which is precisely why "the Fed" cannot be a residual. A residual is something you cannot name. We can name this. It has a trigger, a lag, a coverage, and an object — and history has given us the calibration point.

## The calibration lesson of March 2020

Three facts the next model should encode:

1. **Price tools do not stop margin cascades.** Rate cuts and treasury QE change the discount rate, not the margin call. Expect them to fail against liquidation-driven falls.
2. **Lagged flow tools truncate the tail at the intervention date.** The window was 20 days. If a backstop of the correct object arrives at lag τ, the deepest bucket that fires before τ is your new p99. March 23 makes τ = 20 days the empirical anchor for "flow tool, large developed equity market."
3. **"As needed" is a different instrument than "700 billion."** A bounded number is a price tool in disguise — the market can price the limit. An unbounded commitment absorbs the *expectation* of forced selling, which is what breaks the feedback loop. The market bottomed on the same day the ceiling disappeared.

## Next in the simulator

I am now building this into the model as the next module: a policy layer that takes `(trigger_t, lag_t, coverage, object)` and races the backstop clock against the margin cascade, with the March 2020 calendar as the calibration case. The output I want is not "VaR with a Fed adjustment." It is a distribution whose tail is *truncated at a named date* — because in 2020, the tail did not end at a price. It ended at a press conference.

---

*This article was written with AI assistance and reviewed by the author.*

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*
