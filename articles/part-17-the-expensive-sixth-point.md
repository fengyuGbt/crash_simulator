# The Expensive Sixth Point: Convexity, Thresholds, and the Price of Tail Risk

*Fat Tail Notes · Part 17 · V10-P5*

Last week we argued that the disagreement over the Greenspan put is a measurement problem: expected welfare has no tail, and tail risk has no average. This week we price the tail properly, and the price turns out to be worse than the mean tells you. A -25% drawdown and a -31% drawdown differ by six points. Their social costs do not differ by six points. The sixth point is the expensive one.

## 1. The evidence that crisis costs are convex

Before our own numbers, three independent literatures, none of them ours, all say the same thing: the damage function is not linear in the size of the crisis.

**Persistence.** Cerra and Saxena's *Growth Dynamics: The Myth of Economic Recovery* (2008) is the canonical statement: contractions are not followed by offsetting fast recoveries. On average, the trend output lost is never regained; the output costs of financial crises are permanent. A recent study of 180 economic disasters across 38 countries (Ori & Peri, 2023) is more specific: output loss surges past 26% in the first years after an extreme crisis and stays above 20% for as long as twenty years; full recovery takes over fifty years. Boyd, Kwak and Smith (2005) compute present values: average crisis-related losses are between 63% and 302% of pre-crisis per-capita GDP, because post-crisis slowdowns persist long after the crisis is "officially" over. A 25% drawdown that recovers is a cost. A 31% drawdown that does not recover is a different species of cost.

**Heavy-tailed severity.** Laeven and Valencia's systemic banking crises database (151 episodes, 1970–2017) is the standard distribution of crisis outcomes, and it is not a thin-tailed one. Kapp and Vega take the logical next step for our purposes: they apply the insurance industry's Loss Distribution Approach — frequency times severity, exactly the catastrophe-modeling machinery this series started from — to financial crises, and estimate a multi-country GDP loss distribution. The catastrophe framework is not an analogy we borrowed to look sophisticated. It is the correct tool, because crisis losses behave like disaster losses: rare, severe, and heavy-tailed.

**Political aftershocks.** Funke, Schularick and Trebesch (*Going to Extremes: Politics after Financial Crises, 1870–2014*) study 800+ elections across 20 advanced economies. After a financial crisis, far-right parties gain, on average, 30% in vote share — and critically, they find *no such dynamics in normal recessions or non-financial macroeconomic shocks*. Mian, Sufi and Trebbi document the mechanism: crises polarize voters, weaken ruling coalitions, and reduce the odds of exactly the financial reforms that would help. The tail event does not just destroy wealth; it changes the political system that decides how the losses are distributed. No linear cost function contains that.

## 2. Three lenses on the same Monte Carlo table

Our simulator draws 2,000 shocks, seed 20260921, and runs them through two worlds: exogenous leverage (λ = 1.0) and policy-endogenous leverage (λ drawn above 1 — the world the backstop creates). Last week we published the mean, p10, and p1 columns. This week we add two cost columns: a power cost C(L) = (−L)², and a threshold cost that adds a fixed jump once the drawdown crosses 30% — the regime where cascades, dealer gamma flips, liquidity gaps, and political aftershocks begin. All numbers below are exact output of `crisis_cost_nonlinearity.py` (V10-P5), same seed, same 2,000 paths as Part 15 and 16.

| scenario | mean | p10 | p1 | E[C²] | E[C_thr] | paths > 30% |
|---|---|---|---|---|---|---|
| no backstop, λ=1.0 | -34.1% | -41.0% | -43.9% | 0.1245 | 0.7701 | 85.8% |
| backstop, λ=1.0 | -21.3% | -23.2% | -24.8% | 0.0473 | 0.2134 | 0.1% |
| backstop, λ~N(1.35,0.25) | -24.5% | -27.5% | -29.4% | 0.0616 | 0.2466 | 0.4% |
| backstop, λ~N(1.5,0.30) | -25.5% | -28.4% | -30.4% | 0.0663 | 0.2632 | 1.7% |
| backstop, λ~N(1.75,0.35) | -26.9% | -29.5% | -31.1% | 0.0732 | 0.2973 | 5.7% |

**Lens one — the mean.** The backstop rescues the mean by 12.8 points (-34.1% → -21.3%). Endogenous leverage eats 5.6 of those back (-21.3% → -26.9%), 44% of the rescue. By this lens, the policy is doing its job, with some slippage.

**Lens two — convex cost.** Under C(L) = (−L)², the same rescue is worth 0.077 cost units (0.1245 → 0.0473); endogenous leverage eats 0.026, 34%. Notice something important: the *share* eaten is smaller than under the mean. That is Jensen's inequality working for the policy for once — the rescue is concentrated where the squared cost is largest, so the convexity magnifies the rescue as well as the erosion. The honest reading is not "convexity makes moral hazard smaller"; it is that both the value of the policy and the cost of the leverage it induces live in the tail, and the mean can only report their average.

**Lens three — the threshold.** This is the uncomfortable one. The exogenous backstop puts the 1st percentile at -24.8%, safely inside the 30% line; only 0.1% of paths cross it. Let leverage become endogenous at λ~N(1.75, 0.35) and the p1 moves to -31.1% — **across the threshold** — and the share of paths in the cascade zone rises 57-fold, from 0.1% to 5.7%. Expected threshold cost rises from 0.2134 to 0.2973, a 39% increase in the cost the policy exists to prevent.

The mean does not see this. In mean terms, the λ~1.75 world sits at -26.9%, still 7.2 points away from the no-backstop world — the rescue, by that measure, still looks structurally intact. The tail tells a different story: the worst 1% of outcomes has already crossed the line the policy promised to defend. Six points of mean slippage look like a second-order correction. Six points at the 1st percentile are a first-order regime change.

## 3. The patient, again, with better measurements

Last week's doctor analogy: the painkiller lowers mean pain from 7 to 4 but worsens the worst day from 9 to 10. This week we add the detail the doctor was missing. The question is not just "what is the worst day now?" It is "what happens when a patient crosses the line where the injury stops healing?" A 9 and a 10 on the pain scale are one point apart. But if 10 is the day the patient's joint gives out, the difference is not one point of pain — it is a joint that no longer works. That is what a threshold does: it converts a small difference on the measurement scale into a categorical difference in the outcome.

The leverage the backstop induces is a subsidy to stand closer to the threshold. Most of the time it looks harmless — that is what 0.1% vs 5.7% means from the outside: rare. But "rare" is exactly the object this series has been modeling since Part 1, and the probability is not a constant; it is a function of the policy itself. The exogenous world put the worst percentile inside the line. The endogenous world puts it across.

## 4. What this means for a retail investor

Three rules fall out of the threshold view, and none of them requires you to forecast the next crisis.

First, **price the tail with a convex function, not an average.** If you estimate your crisis risk by expected loss, you are using the lens that hides the threshold-crossing. The difference between "protect the p1" and "improve the mean" is not a nuance; it is the whole argument about what insurance is for. Retail investors rarely do the first. That is the gap this series keeps circling.

Second, **the policy floor has a location, and it moves.** A backstop is not a flat guarantee; it is a line in the distribution, and the line's effective position depends on how much leverage it induces. When you hear "the Fed put is back," ask not whether it exists but *where* it sits in the current book structure. The same policy that looked like a floor at -25% looks like a trap at -31%, because by then the cascade and the politics are already doing their work.

Third, **"six more points" is the wrong mental unit.** The cost difference between -25% and -31% is not 6/25 of your loss — it is the probability-weighted cost of everything beyond the threshold: forced liquidations, gamma flips, policy-space exhaustion, and the political aftershocks that turn a market event into a regulatory one. The sixth point buys you across the line. That is why tail hedges that look expensive in calm markets are not overpriced; they are priced against the threshold, and the threshold is what the leverage cycle quietly moves toward you.

## 5. Where this leaves the series

Part 16 said the moral-hazard debate is really a measurement debate. Part 17 says the measurement that matters is convex and thresholded, not linear and averaged. The academic literatures — persistence, severity distribution, political aftershock — are consistent with each other and with our simulator: the backstop's value and its cost are both in the tail, and the mean cannot arbitrate between them.

A note on method: this series has now published numbers from four V10 modules (backstop, expectations, anticipation, moral hazard) and this one (convex cost), all deterministic, all self-tested, all reproducible with the same seed. The numbers in this post are the exact output of `crash_simulator_v10/crisis_cost_nonlinearity.py` (V10-P5), 204 lines of dependency-free Python with a self-test, run with the series' standard seed. If you can run Python, you can check every number above in under a minute.

Next: if the tail is priced by a threshold, the next question is what happens when the policy space itself is the constraint — the day the backstop cannot backstop. The twenty-day window had a clock. The backstop may have one too.

---

*Code: `crash_simulator_v10/crisis_cost_nonlinearity.py` (V10-P5), self-test and Monte Carlo included. Deterministic, stdlib only, 204 lines. Numbers above are exact output with seed 20260921.*

*Papers: Cerra & Saxena, "Growth Dynamics: The Myth of Economic Recovery" (2008); Ori & Peri, "Recovery from Economic Disasters" (2023); Boyd, Kwak & Smith (2005); Laeven & Valencia, "Systemic Banking Crises Database II" (IMF, 2020); Kapp & Vega, "Real Output Costs of Financial Crises: A Loss Distribution Approach"; Funke, Schularick & Trebesch, "Going to Extremes: Politics after Financial Crises, 1870–2014"; Mian, Sufi & Trebbi, "Resolving Debt Overhang" (2014).*

*Available for freelance work — Python pipelines, quantitative risk tooling, AI data automation. Reach me at gopipibank@gmail.com.*

*Drafted with AI assistance; facts, figures, and errors are the author's own.*
