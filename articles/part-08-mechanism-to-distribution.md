# What a Single 3.07x Hides: From Mechanism to Distribution

**Part 5 reported that under the September 4 market state, a -5% shock becomes -15.4% — a 3.07x amplification. A reader pushed back with the most useful question of the series: *"the aftermath should be non-linear and uncertain — a probability distribution of outcomes, not a single number."* They are right. This article is the answer: V9-P4 wraps the mechanism in a Monte Carlo shell, and the single 3.07x turns out to be the *median* of a distribution that runs to -32%.**

---

## First, the correction promised last time

A reader also caught a data bug in Part 6: I labeled the market state "September 7" — which was Labor Day, a closed U.S. market. Cboe's VIX history file carried a holiday-stub row; my pipeline took the last row blindly. Fixed in the code (weekend filter + align VIX and SKEW on their latest *common* trading date). The corrected state for that article: **September 4, VIX 14.53 (18th percentile), SKEW 151.58 (83rd)**. The conclusion didn't change — calm volatility, expensive tail protection, short-gamma accumulation. The dates are now right. Moving on.

## Where the 3.07x came from

The dealer-gamma module runs a one-line feedback loop:

```
hedge_flow = -κ · net_gamma · price_move      # dealers rebalance delta
next_move  = α · move + β · hedge_flow        # their hedging moves price
```

With net gamma estimated at **-0.666** (from SKEW at the 83rd percentile) and a -5% shock, the loop compounds to -15.4% — **3.07x**. Deterministic, reproducible, single path.

The reader's objection applies to exactly this number. Look at the two inputs:

- **net_gamma is estimated, not observed.** No free OCC options data — the -0.666 is inferred from VIX/SKEW percentiles. It has a sign and a magnitude regime that are structurally right, but it is not a measured position.
- **-5% is a scenario, not a fact.** We chose it to *test* the mechanism. The next real shock will be bigger, smaller, faster, slower.

A single path built on two assumptions is a *story*, not a forecast. The fix is not to abandon the mechanism — it's to make the assumptions explicit as a distribution and see what the mechanism produces across all of them.

## The module: mechanism in, distribution out

`mc_mechanism.py` keeps the deterministic spiral untouched and adds a sampling shell:

| Input | Prior (documented, configurable) |
|---|---|
| net gamma | clipped normal: mean -0.666, σ 0.15, range [-1.0, 0.0] (state implies short gamma) |
| shock size | clipped normal: mean -5%, σ 2%, range [-12%, -1%] |
| paths | 2,000, fixed seed (reproducible) |

Each path: draw a gamma and a shock → run the same deterministic spiral → record the drawdown. Output: the distribution of outcomes plus an exceedance-probability curve — the standard catastrophe-modeling output (EP curve) applied to the mechanism layer, not just to historical replays.

## What the distribution says

| Drawdown | Value |
|---|---|
| Single path (Part 5) | **-15.4%** (3.07x) |
| Median (p50) | **-15.3%** |
| p10 (10% of paths worse) | **-22.8%** |
| p1 (1% of paths worse) | **-28.1%** |
| Worst of 2,000 | **-32.1%** |

**The single 3.07x is the median.** It was never wrong — it was incomplete. The reader's point lands precisely: report a distribution, and the honest headline becomes *"under this state, a -5% shock produces somewhere between -15% and -32%, with a median near -15% and a 1-in-100 tail near -28%."*

The EP curve says it in the form a risk report actually uses:

| P(drawdown ≤ …) | Probability |
|---|---|
| -10% | 95% |
| -15% | 52% |
| -20% | 21% |
| -25% | ~5% |

Half the paths cross -15%; one in five crosses -20%. That is the distribution the single number was hiding.

## What this does to the intervention story

Part 4/7's backstop (2020-style: cut the *flow* of forced selling) was shown on single paths. In distribution form it behaves exactly as it should — it compresses the tail, not the center:

| Tail metric | No intervention | Flow cut |
|---|---|---|
| p1 | -28.1% | **-26.1%** |
| Worst of 2,000 | -32.1% | **-30.2%** |
| Median | -15.3% | -15.3% (unchanged) |

A flow cut doesn't change what an *average* path does — the mechanism still amplifies. What it changes is the *tail*: the rare, worst-case paths get shallower. That is precisely the 2020 story in distribution form, and it is the difference between "the Fed helps a bit" and "the Fed shortens the left tail of the loss distribution."

## The honest boundaries

- **The priors are documented assumptions, not calibrated fits.** The distribution's width is *chosen* (σ 0.15 on gamma, σ 2% on shock). Real widths need real positioning data — which is exactly the data that isn't free. The point is the *structure*: mechanism + explicit uncertainty → tail distribution. The exact percentiles will move with better priors.
- **The kernel is still deterministic.** This module adds uncertainty *around* the mechanism; it does not yet let gamma *evolve* path-by-path (regime shifts mid-crash, cascading defaults). That's the next step up the ladder.
- **EP probabilities are within-model.** P(drawdown ≤ -20%) = 21% means *under these priors and this mechanism*; it is not a claim about calendar time.

## What's next

The mechanism layer asked "what structure could produce the tail." The distribution layer asks "how big is the tail, given what we don't know." The remaining gap is the one that keeps appearing in this series: *implied* state — dealer positions, margin thresholds, options flows — measured from the book, not inferred from indices. That data is expensive. Until then, models like this are how you make the uncertainty visible instead of hiding it in a single number.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)** — commit `3595729` adds the Monte Carlo shell.

I write about fat tails, risk engineering, and AI automation at **Fat Tail Notes**. If you've seen a risk report that quotes one number where a distribution belongs — or the opposite — I'd love to hear your version.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*Built with Python and the habit of letting reader feedback become the roadmap.*

---

*This article was written with AI assistance and reviewed by the author.*
