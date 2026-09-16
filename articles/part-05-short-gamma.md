# Short Gamma: The Market-Maker Spiral

**In my last article I described the margin spiral — leverage feeding on itself until a correction becomes a crash. This one is the same loop, one level down, in the plumbing of the market. The actors aren't leveraged funds this time. They're the market makers who are supposed to keep prices smooth. And their mechanical hedging, in a selloff, does exactly the opposite: it manufactures the crash they're paid to absorb.**

---

Here's the setup. On September 7, 2026, my market-state module read:

- **VIX: 15.3** — 25th percentile of five years. Calm.
- **SKEW: 151.58** — 83rd percentile. Tail protection is expensive.

Calm market, expensive crash insurance. I wrote about that contradiction in Part 3. But there's something hiding behind it that most models don't see: **expensive put protection means someone sold those puts — and that someone is usually a market maker, now holding a position that makes them mechanically sell into falling markets.**

## The gamma position

Gamma measures how fast an option's delta changes as the underlying moves. Market makers don't take directional bets — they run delta-neutral books, continuously rebalancing to stay flat. The question is *what their rebalancing does to the market.*

- **Long gamma** (they own options): price falls → their delta falls → to stay neutral they **buy**. Buying into a fall is stabilizing. Dealers long gamma are the shock absorbers.
- **Short gamma** (they sold options): price falls → their delta rises → to stay neutral they **sell**. Selling into a fall is amplifying. Dealers short gamma are the accelerant.

Same obligation — stay delta neutral — completely different effect on the market. And the sign is decided by which side of the trade the dealer is on.

## Why dealers end up short gamma

The economics of market making push the book in one direction. Clients overwhelmingly want to **buy** protection — puts on indexes, downside collars, crash insurance. Someone has to sell that protection, and the seller takes the short-gamma side. The dealer collects the premium (and the theta), but inherits the position that forces them to sell as the market falls.

Here's the tell: **SKEW is a shadow of dealer positioning.** When SKEW is high, clients have paid up for tail protection, which means the dealer's net position is more short gamma. The index that everyone reads as "fear" is also a gauge of how much mechanical selling is hiding in the market.

## The spiral, with numbers

My V9 module (`src/dealer_gamma.py`) models this as a feedback loop — the same structure as the margin spiral, different actors:

```
price falls → dealer delta rises → mechanical hedge selling → price falls more
```

Running it with the actual September 7 market state:

| Scenario | Amplification of a -5% shock |
|---|---|
| No dealer gamma (baseline) | 2.38× → about -12% |
| **Net dealer gamma -0.67 (from SKEW 83rd pctile)** | **3.07× → about -15.4%** |
| Same, with an intervention at -6% | 2.85× → spiral damped |

A 5% move that a naive model calls "a bad day" becomes, through the dealer-hedging mechanism alone, a 15% drawdown. The extra 3-4 points didn't come from news. **They came from the market's own plumbing.** The model estimates net dealer gamma at -0.67 — not an extreme reading, just "tail protection is expensive" — and the amplification is already there.

This is also why interventions matter so much. In the simulation, an intervention that provides liquidity once the drop reaches -6% cuts the amplification from 3.07 to 2.85. Not a fix — a brake. Which is exactly how 2020's central-bank response read in hindsight: don't change the news, change the loop.

## Why classical models miss it

A standard VaR model treats the portfolio as a price taker: you observe price moves, you compute losses. The dealer spiral breaks that assumption in a specific way — **the hedger's loss is the market's price move.** The feedback is the same shape as the margin spiral from Part 4, which is why I model them with the same framework:

```
portfolio leverage  → margin calls  → forced selling  → prices fall  → more margin calls
dealer short gamma  → delta hedge   → mechanical selling → prices fall → more hedging
```

One loop in the books of leveraged funds, one loop in the books of dealers. Same mathematics, same blind spot in classical models: **the part of the loss that the market causes to itself.**

## Three things to take away

1. **SKEW isn't just fear — it's a positioning map.** High SKEW means someone is short gamma, and that position turns ordinary selloffs into mechanical selling pressure. When SKEW is elevated, a calm VIX is a quieter danger, not a safer one.

2. **Low volatility + expensive protection = accumulated short gamma.** The regime that feels safest (calm VIX) is often the one where volatility sellers have stacked up. The crash risk isn't in the volatility level; it's in the dealer book hidden under it.

3. **Model the flow, not just the position.** Saying "dealers are short gamma" describes a state. The loss only appears when you model the *flow* — the mechanical selling that follows each tick lower. State models miss it; loop models catch it.

## What's next: closing the loop on endogeneity

Dean's feedback, which started this V9 line, had three parts. Part 1 (endogeneity) got answered by the system-dynamics article. Part 2 (dealer short gamma) is this article and the code behind it. Part 3 (implied over realized calibration) got the SKEW article. The last piece is to wire the gamma state into the hazard layer itself — so the probability of a crash becomes a function of the market's own state, including how much mechanical selling is hiding in it. That's V9-P2, and it's next.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)**

I write about fat tails, risk engineering, and AI automation at **Fat Tail Notes**. If you trade options for a living — or you've watched dealer flows do something surprising in a selloff — I'd love to hear your version of this loop.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*Built with Python, free Cboe data, and a healthy respect for the fact that the market's plumbing is part of the market.*

---

*This article was written with AI assistance and reviewed by the author.*
