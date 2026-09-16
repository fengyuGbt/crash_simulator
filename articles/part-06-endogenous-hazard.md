# Endogenous Hazard: The Model Starts Listening to the Market

**Three articles ago I wrote that "endogeneity" was the deepest of the three critiques a derivatives-savvy reader made of my crash simulator. Two articles ago I built the margin spiral. Last article I built the dealer short-gamma spiral and ended with: "The last piece is to wire the gamma state into the hazard layer itself — that's V9-P2, and it's next." It's done. This is the closing of that loop.**

---

## The loop, closed

The hazard layer of a catastrophe-modeling framework answers: *what extreme events can happen, how big, how often?* In my simulator's original design that layer was **exogenous** — a fixed list of six historical crashes (2008 at -56.8%, 2000 at -78%, 2022 at -75%...) plus random noise around each replay. The market state never touched it. A calm market and a panic market replayed history the same way.

That was exactly the blind spot Dean pointed at: *"in capital markets, the hazard layer is created by the financial contracts themselves."* The market's own state — how much protection people have bought, how short gamma the dealers are — changes how an exogenous shock unfolds. So I wired it in.

```
event intensity = historical noise × regime multiplier × short-gamma factor
```

- **Regime multiplier** comes from the VIX/SKEW state module: calm ×1.0, stressed ×1.5, panic ×2.5.
- **Short-gamma factor** comes from the dealer-gamma module: 1 + max(0, -net_gamma) × 0.30, capped at 1.5.

## The number that matters

Running it on the September 7 market state:

| Input | Value |
|---|---|
| VIX | 15.3 — 25th percentile of five years. **Calm.** |
| SKEW | 151.58 — 83rd percentile. Tail protection expensive. |
| Regime | calm → multiplier **1.0** |
| Estimated net dealer gamma | **-0.666** |
| Combined state intensity multiplier | **1.1998** |
| Mean |drop|, calibrated vs baseline | 0.575 vs 0.479 — **about +20%** |

Read that carefully. **The market was calm.** The regime multiplier did nothing — it was 1.0. And yet the hazard layer still replayed historical crashes about 20% harder than before, purely because of the short-gamma term. SKEW at the 83rd percentile means clients have paid up for tail protection, which means dealers are net short gamma, which means mechanical hedge selling will amplify any selloff that starts.

This is the sentence from Part 5 — *"low volatility + expensive protection = accumulated short gamma"* — promoted from prose to code behavior. The model doesn't just tell you the market is calm; it tells you that calm contains an amplifier.

## Why this closes the loop

Classical models treat hazard as a list of external facts: these events happened, at these frequencies, with these severities. The market state is an input to the *loss* calculation, never to the *danger* calculation.

The endogenous version makes danger itself state-dependent:

- **High VIX** → stressed/panic regime → the same historical event replays harder (×1.5 or ×2.5)
- **High SKEW with low VIX** → short-gamma accumulation → mechanical selling amplifier on top of the regime multiplier
- **Both quiet** → the model still lifts replay intensity, because expensive protection is itself a hazard signal

The result: a market that *looks* safe on VIX alone now carries its own fragility in the hazard layer — which is precisely what the endogeneity critique demanded. The contracts people wrote (put protection, volatility sales) became part of the danger.

## The honest boundaries

This is a **mechanism model**, and I want the limits stated as plainly as the results:

- **Net gamma is estimated, not observed.** Full options-chain positioning (OCC data) is not freely available, so net dealer gamma is approximated from SKEW/VIX percentiles. The *sign* and *direction* are structurally right; the point estimate is not a calibrated GEX number.
- **The 0.30 weight is a mechanism parameter, not a market fit.** I document it, it has a cap, and it's configurable — the point is the feedback structure, not the precise multiplier.
- **The +20% is a within-model result.** It says: *given this state and this mechanism, historical crashes replay harder.* It does not claim the next crash will be 20% worse.

Mechanism models earn their keep differently: they tell you *what structure could produce the tail*, and where to look for the real data. That's the discipline Dean pushed for — implied distributions over realized history — applied to my own architecture.

## What's next: the feedback continues

Dean's latest comment on Part 4 added two sharper edges:

1. **Forced selling is not a continuous ODE.** Brokers mark at discrete intervals, thresholds sit on round numbers many accounts share, so liquidation arrives in *steps*, not a slope. His example: a 10% print can skip 12% and land at 18% because everyone triggers at 15% together. That's a discrete-threshold model — a natural V9-P3.
2. **The liquidation window.** A VaR that treats the Fed as a residual prices the news shock but not *how long the forced-selling flow stays open*. Making that window measurable is the next problem.

So the loop isn't finished — it's finally running. The hazard layer reads the market, the market's feedback shows up in Dean's comments, and the comments become the next module.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)** — commit `beb1ae1` wires the state in.

I write about fat tails, risk engineering, and AI automation at **Fat Tail Notes**. If you've watched a "calm" market hide an amplifier — dealer books, margin thresholds, options flows — I'd love to hear your version.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*Built with Python, free Cboe data, and the habit of letting market feedback become the roadmap.*

---

*This article was written with AI assistance and reviewed by the author.*
