# The Cascade Runs Ahead of the Flip

**Part 9 added the gamma flip: vol spikes, dealer books turn from short to long gamma, and the selling spiral is truncated. That's half the story. The uncomfortable other half: the flip is not instant, and while it converges, leveraged accounts are being force-liquidated on their own schedule. This article is the race — V9-P6 puts margin cascades next to the flip, and the honest result is that even a timely flip does not save everyone. March 2020's survivors weren't the funds that were structurally safe; they were the ones that hadn't blown up yet.**

---

## The detail Part 9 glossed over

The flip story, as told so far, is clean: short gamma feeds the spiral, vol spike flips the book, the spiral dies. But a crash doesn't wait politely for the book to turn positive. While gamma is converging, three other things are happening on top of the price fall:

1. **10x accounts** breach their maintenance margin and get a margin call.
2. The call has a **grace window** — days, not microseconds.
3. When the window closes, the position is **force-sold**, and that sale hits the market like any other sale.

Margin calls don't cancel because gamma flipped. The forced sales have their own momentum — and their own timetable. So the real question isn't "does the flip stop the crash?" It's: **does the flip stop the crash before the cascade finishes?**

## The model: two engines, one race

`cascade.py` adds one structure to the Part-5 kernel: leveraged accounts in four buckets, each with a leverage, a portfolio weight, and a price trigger at which it gets liquidated:

| Bucket | Leverage | Weight | Trigger |
|---|---|---|---|
| A | 10x | 10% | -5% |
| B | 5x | 20% | -10% |
| C | 3x | 30% | -15% |
| D | 2x | 40% | -20% |

When a bucket trips, its forced selling releases over **3 steps** — the margin-call grace window — so the liquidation keeps feeding the market while the flip converges. Everything else is the same kernel: dealer hedging, the flip rule, the α/β dynamics.

## What the race looks like

| Setup | Drawdown | Amplification |
|---|---|---|
| Bare spiral (Part 5) | -15.4% | 3.07x |
| Spiral + flip (Part 9) | -13.8% | 2.76x |
| Spiral + flip + cascade | **-19.3%** | **3.85x** |

Read the timing carefully: **the flip fires at step 3. The last liquidation happens at step 7.** The gamma book turns positive early — and the cascade keeps doing damage for four more steps anyway. The cascade's share of the total loss is 28%.

That is the mechanism's version of March 2020: the dealer side *did* stabilize; the leveraged side was still being unwound on its own clock. "The market stabilized" and "funds kept blowing up" are both true, because they are two different engines.

## Flip timing is now a race, not a dial

Part 9's threshold sweep showed the flip gets less effective the later it fires. The cascade makes the stakes explicit — the flip is now racing the liquidation schedule:

| Flip threshold | Buckets liquidated | Drawdown |
|---|---|---|
| 5% | 3 of 4 | -15.7% |
| 10% | 3 of 4 | -19.3% |
| 15% | 4 of 4 | -21.9% |
| 20% | 4 of 4 | -23.5% |

The gap between an early self-heal and a late one is **7.8 points** — and the late-heal case liquidates every bucket. When the flip fires after the 3x bucket (15%), the damage converges to the full cascade: nothing is left to save.

## The distribution view

With uncertain gamma, shock, and flip timing (same priors, 2,000 paths):

| Metric | No cascade | With cascade |
|---|---|---|
| Median | -15.5% | **-19.2%** |
| p10 | -22.7% | **-28.9%** |
| p1 | -28.6% | **-33.5%** |
| Worst | -33.4% | **-36.6%** |

Average path liquidates **2.9 of 4 buckets** — the typical crash, in this model, unwinds most of the leveraged book even with a working flip. And the tail deepens by ~10 points at p1. The flip shortens the *dealer* tail; the cascade owns the *leverage* tail, and the two don't cancel.

## What this means for the "self-healing market" story

Part 9 made the careful point that the flip stops the crash but doesn't reverse it. Part 10 sharpens it: **the flip doesn't even stop all the selling.** It stops the *dealer* selling. The leveraged selling has its own trigger logic, its own grace windows, its own timetable — and it runs to completion unless something interrupts *it*.

This is why the 2020 policy response targeted *both* engines. The vol spike (and eventually Fed backstops on credit markets) handled the dealer side; liquidity provision — the "don't force funds to sell into the abyss" piece — handled the cascade side. A policy that only stabilizes dealers leaves the cascade running. A model that only models dealers misses the same thing.

## Boundaries

- The buckets (leverage, weight, trigger) are a **documented stylization**, not a fitted margin map. Real books are messier and more correlated.
- The 3-step release is a stand-in for grace windows that vary by counterparty and jurisdiction.
- What this module does *not* yet do: **contagion between the two engines** — the same forced sale that pushes price down also moves the vol surface that triggers the flip; the cascade and the flip are coupled through price, but not through the vol surface itself.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)** — commit `a35de56` adds the margin cascade.

The series now covers the full crash in three acts: the mechanism that deepens it (gamma spiral), the mechanism that stops the dealer side (gamma flip), and the engine that keeps running anyway (margin cascade). If you've sat through a real liquidation queue — margin calls, grace windows, forced sales — I'd like to know what the timetable looked like from inside.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*This article was written with AI assistance and reviewed by the author.*
