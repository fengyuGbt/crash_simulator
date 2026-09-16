# Why the Spiral Stops: The Gamma Flip

**The dealer short-gamma spiral is the series' best story: a selloff forces mechanical hedging, which deepens the selloff. Part 5 turned that loop into 3.07x; Part 8 showed the number was the median of a distribution running to -32%. One thing stayed uncomfortable: in the real world, spirals stop. March 2020 didn't go to zero — it stabilized, then rebounded. This article closes the gap: V9-P5 adds the gamma flip to the kernel, and the mechanism finally explains both halves of a crash — why it deepens, and why it ends.**

---

## The uncomfortable fact: spirals terminate

Every mechanism in this series so far has been self-amplifying. Short gamma begets selling; selling begets more short-gamma pressure; margin calls cascade. Run the loop long enough and you get -32%, -50%, worse. Markets don't do that. Even 2008 and 2020 bottomed out.

Why? Because the *position* that drives the spiral is not fixed. The short-gamma dealer is short *because* selling tail protection was profitable. When the tail actually arrives, that trade becomes violently unprofitable — implied volatility explodes, and the dealer's book flips: forced to sell on the way down, mechanically attracted to *buy* once the vol spike reprices the position. Short gamma becomes long gamma. The selling engine runs out of fuel.

That's the **gamma flip**, and it is the mechanism that turns a crash into a bottom.

## The model: one evolution rule on top of the Part-5 kernel

V9-P4's honest boundary said the kernel didn't yet let gamma evolve path-by-path. `gamma_flip.py` adds exactly one rule:

```
gamma starts at -0.666 (short)                        # Part-5 estimate
once cumulative drawdown passes flip_threshold:
    gamma converges toward +0.80 (deep long gamma)     # vol spike flips the book
```

Everything else — the `hedge_flow = -κ·γ·ret` feedback, the α/β dynamics — is untouched. One rule, one new parameter family: *when* the flip happens (threshold), *how hard* it lands (target), *how fast* it bites (speed).

## What the flip does to the single path

With the default threshold (10%):

| Path | Drawdown | Amplification |
|---|---|---|
| No flip (Part-5 baseline) | **-15.4%** | 3.07x |
| Flip at -10% | **-13.8%** | 2.76x |

The price path tells the real story — it *stabilizes*:

```
no flip:  1.00 → 0.95 → 0.92 → 0.89 → 0.87 → 0.86 → 0.85 → … → 0.846
with flip: 1.00 → 0.95 → 0.92 → 0.89 → 0.87 → 0.870 → 0.866 → 0.864 → 0.862 (flat)
```

Flip fires at step 3 (gamma flips -0.666 → +0.80), and the descent stops. Not a V-shaped recovery — a *truncated* crash. That distinction matters.

## When the flip fires is everything

Sweep the threshold — i.e., ask "how much damage does the market tolerate before the flip?":

| Flip threshold | Drawdown | Amplification | Flip step |
|---|---|---|---|
| -5% | -11.9% | 2.39x | 1 |
| -8% | -13.0% | 2.61x | 2 |
| -10% | -13.8% | 2.76x | 3 |
| -15% | -15.4% | 3.07x | 10 (too late) |
| -20%+ | -15.4% | 3.07x | never |

The pattern is brutally monotone: **the later the market "self-heals," the more the damage converges to the full spiral.** Below ~10% the flip materially truncates the crash; at 15% it's already too late — the damage is done before the positions flip. Thresholds, in other words, are not a detail. They are the whole game.

## The distribution view (Part 8's language)

With uncertain gamma0 / shock / threshold (same priors as V9-P4, 2,000 paths):

| Metric | No flip | With flip |
|---|---|---|
| Median | -15.5% | **-14.0%** |
| p10 | -22.7% | **-19.4%** |
| p1 | -28.6% | **-23.7%** |
| Worst | -33.4% | **-27.2%** |

The flip fires in 80% of paths, and it does what Part 8 showed interventions do: it compresses the *tail*, not the center. Median moves ~1.5pp; p1 moves ~5pp; worst moves ~6pp. The mechanism's self-termination is a tail-shortener by construction.

## The honest division of labor

This is the part I want to be careful about. **The gamma flip stops the crash; it does not reverse it.** In this model, price stabilizes — it does not recover. The V-shaped rebound of March 2020 came from a different engine: the Fed's QE, which this series models as *intervention* (flow cut). So the complete 2020 story, in mechanism terms, has two distinct acts:

1. **Vol spike flips dealer gamma** → the selling spiral is truncated (this module).
2. **Liquidity injection reverses the flow** → the stabilization becomes a recovery (the intervention modules).

Mixing those two acts into one "the market self-corrects" narrative would be wrong — and it's exactly the kind of conflation that produces bad policy conclusions ("no need to intervene, the market will heal itself"). The flip is real, and it is *not* a substitute for intervention. It converts an uncontrolled spiral into a controlled stabilization; whether that stabilization becomes a recovery is a separate, policy-driven question.

## Boundaries

- The flip rule is a **documented stylization**, not a fitted model. Real flips are messier (they involve specific dealer books, vol-surface repricing, forced liquidations *within* the flip).
- The threshold is not calibrated to data. The sweep is the honest way to read it: this is how sensitive the tail is to the timing of the flip.
- What this module does *not* yet do: model the **cascade inside the flip** — the funds that blow up before the book turns positive. That's the next rung: short-gamma → vol spike → forced liquidation → gamma flip as the *end* of a cascade, not the start.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)** — commit `1611737` adds the gamma-flip module.

The series has now covered both directions of a crash: the mechanism that makes it worse, and the mechanism that makes it stop. If you've watched a real drawdown stabilize — or the opposite — I'd like to hear what your book did at the turning point.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*This article was written with AI assistance and reviewed by the author.*
