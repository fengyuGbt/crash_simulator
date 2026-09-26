# The Retail Underwear: What Protection Costs When the Backstop Has a Clock

*Fat Tail Notes · Part 19 · V10-P7*

Part 18 asked the question this series has been walking toward since Part 11: when the backstop's protection is probabilistic, what does the retail investor's own "underwear" actually consist of, and what does it cost? This part answers with numbers. Two garments exist for the unprotected investor — a cash buffer and put insurance — and they have different geometries, different costs, and different failure modes. The cash garment has capacity 1.0 by construction: it is always there. The options garment's capacity is priced by the market, and the market reprices insurance most expensively exactly when it is most needed.

## 1. What the market says protection costs

The survey numbers are consistent across practitioners:

- **Put insurance** (10-20% out-of-the-money, rolled quarterly): roughly 1-3% of portfolio per year. Deep OTM puts (20%+ strikes) cost 1-2% per quarter of protection; put spreads 0.5-1.5%.
- **Crisis repricing**: the same contract costs 2-5x in panicked markets. In March 2020 the VIX went from ~14 to 82; the S&P 500 fell 33.9% in 23 trading days, and puts that cost 1% in calm conditions were quoted at 5-10%. One example in the literature: a deep OTM put at normal IV 30% cost 0.10; at crisis IV 150% the same strike cost 4.50 — a 4,400% repricing.
- **Cash buffer**: the opportunity cost of holding cash is roughly 0.8-1.2% per year for moderate over-allocation, and it compounds brutally over decades.

The uncomfortable structure, and the reason this part exists: **the retail investor's insurance has its own "pushing on a string" problem** — the exact phenomenon Tenreyro and Thwaites documented for monetary policy. Policy is weakest in the state where it is most needed. The retail put is most expensive in the state where it is most needed. Renewal is the clock.

## 2. The model: two garments, two geometries

We reuse the exact market-loss machinery of Parts 15-18 (P4's `run_policy_moral_hazard`, P6's capacity levels C) and overlay the two garments on the raw per-path losses, seed 20260921, 2,000 paths per level:

- **bare** — no garment: loss = market loss.
- **cash** — 20% buffer: every path scaled by 0.8. Deterministic, always works; cost is the calm-market opportunity cost, 2.0%/yr at a 10% equity return assumption.
- **put** — deductible 20%, premium 2%/yr: every path beyond -20% gets paid dollar-for-dollar above the deductible; loss is capped at -(20% + 2%) = -22%. The garment is a hard tail truncation.
- **put_crisis** — same deductible, but the premium is repriced at 6%/yr (2-3x, the survey's crisis renewal): what happens if you buy protection after the vol spike, not before.

| C | garment | mean | p1 | worst | >30% paths |
|---|---|---|---|---|---|
| 1.00 | bare | -24.6% | -29.4% | -31.5% | 0.4% |
| 1.00 | cash | -19.7% | -23.5% | -25.2% | 0.0% |
| 1.00 | put | -21.5% | **-22.0%** | -22.0% | 0.0% |
| 1.00 | put_crisis | -25.5% | -26.0% | -26.0% | 0.0% |
| 0.75 | bare | -30.7% | -55.9% | -61.6% | 27.2% |
| 0.75 | cash | -24.5% | -44.7% | -49.3% | 23.9% |
| 0.75 | put | -21.6% | **-22.0%** | -22.0% | 0.0% |
| 0.50 | bare | -38.6% | -61.3% | -66.1% | 54.9% |
| 0.50 | cash | -30.8% | -49.0% | -52.9% | 49.2% |
| 0.50 | put | -21.8% | **-22.0%** | -22.0% | 0.0% |
| 0.25 | bare | -47.1% | -63.7% | -66.1% | 80.5% |
| 0.25 | cash | -37.6% | -51.0% | -52.9% | 73.8% |
| 0.25 | put | -21.9% | **-22.0%** | -22.0% | 0.0% |
| 0.00 | bare | -33.9% | -44.1% | -46.7% | 84.4% |
| 0.00 | cash | -27.1% | -35.3% | -37.3% | 38.9% |
| 0.00 | put | -20.9% | **-22.0%** | -22.0% | 0.0% |

The geometries are the whole point. The cash garment is a **scaling**: every loss, shallow and deep, is multiplied by 0.8. The put garment is a **truncation**: no path can lose more than 22%, and shallow paths are barely touched. Both cost 2% per year. Their difference only shows in the tail — which is exactly the region the previous three parts said you should be reading.

## 3. The clock reads in the renewal

Tail protection per 1% of cost (p1 improvement over bare):

| C | cash saves | put saves | crisis-put saves |
|---|---|---|---|
| 1.00 | 5.9 pts | 7.4 pts | 3.4 pts |
| 0.75 | 11.2 pts | 33.9 pts | 29.9 pts |
| 0.50 | 12.3 pts | 39.3 pts | 35.3 pts |
| 0.25 | 12.7 pts | 41.7 pts | 37.7 pts |
| 0.00 | 8.8 pts | 22.1 pts | 18.1 pts |

Two findings, both in the real numbers.

**First: the options garment dominates the cash garment in the tail, and the gap widens as policy capacity drains.** At C = 1.00, put and cash are close (7.4 vs 5.9 points saved at the 1st percentile). At C = 0.25, put saves 41.7 points against cash's 12.7 — the same 2% cost buys 3.3x more tail protection when the backstop is depleted. The reason is the truncation geometry: cash scales a -63.7% tail to -51.0%, put pins it at -22.0%. When the market's own backstop is probabilistic (Part 18), the private garment with a hard cap is the one that actually guarantees a floor.

**Second, and more important: the options garment's clock is the renewal, and it is exactly the Part 18 structure in miniature.** Locked at 2%, the put improves both mean and p1 at every capacity level. Repriced at 6% — the survey's crisis renewal, 2-3x — the same garment **drags the mean below bare** in the calm world: at C = 1.00, mean worsens from -21.5% (locked) to -25.5% (renewed), worse than bare's -24.6%. The 6% premium now exceeds the average payout. In the depleted world the renewed put still rescues (-25.9% vs bare -47.1%), but the insurance has quietly become much more expensive exactly at the moment it matters most.

This is the retail version of "pushing on a string": the policy clock of Part 18 — policy is weakest when most needed — has a private-market twin. Your protection is repriced by the same crisis that makes you need it. The put you roll in a panic costs 3x the put you bought in calm. The cash garment has no such repricing: it is the only asset class with capacity 1.0 by construction.

## 4. What the numbers say a retail investor should do

**Wear both, in layers, and buy the options when they are cheap.**

The cash garment is the foundation. It is deterministic, it never fails, its failure mode is behavioral (spending it, panic-deploying it) rather than priced. At every capacity level it improves both mean and tail for 2% a year. There is no market state in which cash is not there.

The options garment is the tail floor, and its purchase timing is the whole game. The 2% locked put and the 6% crisis put have identical payouts and wildly different economics: one improves the mean at every C, the other drags the mean in calm worlds. The difference is not the instrument — it is when you bought it. The rule writes itself: **buy the umbrella in the sun**. Implied volatility is the price of protection, and implied volatility is mean-reverting and crisis-spiking. If you wait for the crisis to buy insurance, you are buying the most expensive insurance at the moment the tail is most likely.

And the Part 18 link makes the timing concrete. Policy capacity is the clock: rate paths, balance-sheet run-off, debt trajectories, central-bank independence. As the clock reads down (C falling), the value of the options garment rises — 7.4 points saved at C = 1.00, 41.7 at C = 0.25. The correct retail behavior is not to predict the crisis; it is to hold the deterministic layer always, and to buy the probabilistic layer while the implied-volatility price still reflects a world in which the backstop looks intact. The market prices the promise. You price the capacity. The clock is read in the tail, and the garment is bought before the clock reads.

Cost-wise, both garments run about 2% of portfolio per year. That is the price of the underwear: a deliberate, recurring, small premium against the region of the distribution where the previous three parts live. The alternative — no garment — is the bare column of the table above.

## 5. Where this leaves the series

Part 18 priced the backstop's clock. Part 19 prices the retail garment that has to exist when the backstop is probabilistic: cash is the deterministic layer (capacity 1.0, always there, bought with opportunity cost), options are the probabilistic layer (hard tail floor, bought cheap or not at all, repriced by the same crisis that creates the need). The two garments cost the same and protect differently; the options garment's clock is its renewal, and the correct response to that clock is to buy protection when its price still assumes the backstop is intact.

The remaining question, and the natural next part: the cash garment's failure mode is behavioral — panic, spending, redeployment at the worst moment. If the numbers say wear both, the discipline of wearing them is a behavioral problem, not a modeling one. That is Part 20.

---

*Code: `crash_simulator_v10/retail_underwear.py` (V10-P7), self-test and Monte Carlo included. Deterministic, stdlib only, 256 lines. Numbers above are exact output with seed 20260921, market losses from the P4/P6 machinery.*

*Survey anchors: protective-put cost structures (1-3%/yr for 10-20% OTM, rolled; 2-5x repricing in crisis); March 2020 (VIX 14->82, S&P -33.9% in 23 days, protection 1% -> 5-10%); cash opportunity cost (0.8-1.2%/yr moderate over-allocation); and the series' own Parts 15-18 modules and seed.*

*Available for freelance work — Python pipelines, quantitative risk tooling, AI data automation. Reach me at gopipibank@gmail.com.*

*Drafted with AI assistance; facts, figures, and errors are the author's own.*
