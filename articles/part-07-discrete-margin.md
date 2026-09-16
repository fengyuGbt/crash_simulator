# Discrete Margin & the Liquidation Window: Why a 10% Print Can Land at 18%

**Last article I closed the endogeneity loop and ended with two sharper edges from a derivatives-savvy reader: "forced selling is not a continuous ODE," and the liquidation window is what a VaR that treats the Fed as a residual never prices. This is the module those two comments produced — V9-P3, `discrete_margin.py`. Same shock, same book: one model arrives in a slope, the other in steps.**

---

## The assumption I was quietly making

My system-dynamics module (Part 4) modeled forced selling as a **continuous flow**: every step, leverage was marked to market, and selling pressure was a smooth function of how far the account sat below its threshold. The math was an ODE, and the output was a slope — a crash that *slides*.

A derivatives person sees three problems with that at once:

1. **Margin is not marked continuously.** Brokers check accounts at intervals — daily, or at prescribed mark points. Between marks, nothing happens even if the price is sitting below a threshold.
2. **Thresholds are not spread out.** They sit on round numbers — 10%, 15%, 20% — and a lot of accounts share the same one. When price crosses 15%, *everyone at 15% triggers in the same batch.*
3. **Batches move price through the book.** The forced sale lands in a thin order book, the price jumps, and the jump itself crosses the next round number — where the next batch is waiting.

That's why, as the comment put it, *"a 10 percent print can skip 12 and land at 18 before anyone has time to add cash."* The ODE assumption smooths out exactly the mechanism that makes crashes step-shaped.

## The three parts of the module

`discrete_margin.py` makes each of those explicit:

| Mechanism | Implementation |
|---|---|
| **Discrete marking** | Margin checked every `mark_interval = 3` steps, not every step |
| **Threshold bunching** | Accounts cluster on round numbers: -10% (25% of accounts), -15% (30%), -20% (25%), -25% (20%) |
| **Batch liquidation** | When price crosses a shared level, the whole bucket dumps at once; the jump can cross the next threshold in the **same mark round** |
| **Liquidation window** | Steps from first to last liquidation + cumulative forced-selling flow — the part VaR never prices |

The comparison object is the old ODE-style release: same thresholds, same book, but selling pressure released smoothly in proportion to the gap. One simulation, two shapes.

## What the same shock does to each model

A -15% exogenous print on both:

```
Step 3 (first mark round, discrete):
  price 0.856 <= 0.90   -> -10% bucket (25%) liquidates  -> price 0.824
  price 0.824 <= 0.85   -> -15% bucket (30%) liquidates  -> price 0.787
  price 0.787 <= 0.80   -> -20% bucket (25%) liquidates  -> price 0.757
  (same mark round: three thresholds crossed, no time to add cash)
Step 6 (next mark): the residual flow drags -25% bucket under too
```

| Metric | Discrete (bunched) | ODE (smooth) |
|---|---|---|
| Max drawdown | **-29.6%** | -15.4% |
| Max single-step jump | **0.121** | 0.004 |
| Loss concentration (jump / total drop) | **0.409** | 0.024 |
| Liquidation events | 4 batches | 1 smooth slope |
| Liquidation window | 3 steps, cumulative flow 0.846 | — |

Read that in Dean's frame: **the same print that slides to -15% in the ODE world *skips three levels in one mark round* and lands near -24% before anyone can react**, ending at -29.6% once the residual flow takes out the last bucket. The tail is not just deeper — it's *step-shaped*. The ODE assumption wasn't conservative; it was structurally blind to the shape of the bad outcome.

## The liquidation window — what the VaR misses

The second comment cut deeper: a risk model that prices the Fed's *reaction* but not the Fed's *absence* — or, equivalently, treats central-bank intervention as an unmodeled residual — is pricing the shock and not the process.

The window has two measurable parts:

- **Duration**: steps between first and last forced liquidation (here, 3)
- **Flow**: cumulative selling that passes through the market while the window is open (here, 0.846 of the book)

The point of making it measurable: **2020 was not "the Fed fixed the news."** It was the Fed shortening the window — absorbing the flow of forced sales (via facilities, backstops, market-maker support) so that selling stopped *feeding on itself* before the next threshold was reached. Cut the flow, and the staircase stops being a staircase.

The module models exactly that as an optional backstop: from a trigger step onward, absorb a fixed amount of selling per step — 2020-style, *cut the flow, not the news*:

| Metric | No intervention | Backstop (flow absorbed) |
|---|---|---|
| Max drawdown | -29.6% | **-28.3%** |
| Cumulative forced-selling flow | 0.846 | **0.648 (−23%)** |
| Terminal price (step 40) | 0.847 | **0.858** |

The flow cut doesn't prevent the first jump — no one can add cash inside a mark round. What it does is shorten the tail: less flow passes through, the -25% bucket never gets dragged under by residuals, and recovery is faster. That is the whole 2020 story in one table: you can't stop the first batch, but you can stop the *cascade*.

## The honest boundaries

- **Mechanism model, not calibration.** Parameters (mark interval, bucket shares, flow impact, backstop timing) are documented and configurable, chosen to exhibit the structure — they are not fitted to any single crash. The claim is about the *shape* of the feedback, not point estimates of the next drawdown.
- **The "skip" is structural, not a forecast.** The module says: *given discrete marking and integer thresholds, batch liquidation jumps through levels in one mark round.* It does not claim the next crash will land exactly at 18% or 24%.
- **The window metric is the deliverable.** The honest contribution is making "how long the forced-selling flow stays open" a number a risk report can carry, instead of a residual.

Mechanism models earn their keep by telling you *what structure could produce the tail, and what to measure next*. The measure next is the actual duration of liquidation windows in real margin books — which, like GEX, is exactly the data that isn't free.

## What's next

The endogeneity loop is closed and the discrete margin layer is in. The remaining hole is the one Dean keeps circling: *implied* state — dealer positioning, margin thresholds, options flows — versus *realized* history. The modules now read the market; the next one should read the *book*.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)** — commit `894cc76` adds the discrete margin layer.

I write about fat tails, risk engineering, and AI automation at **Fat Tail Notes**. If you've watched a crash arrive in steps when the models said it would slide — margin books, forced selling, liquidity windows — I'd love to hear your version.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*Built with Python and the habit of letting market feedback become the roadmap.*

---

*This article was written with AI assistance and reviewed by the author.*
