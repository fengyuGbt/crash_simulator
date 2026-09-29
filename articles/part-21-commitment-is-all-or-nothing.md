# Commitment Is All-or-Nothing: Why the Last Quarter of the Garment Carries the Tail

*Part 21 of the Fat Tail Notes series — pricing the "better default" the retail investor actually needs.*

## The hook

Part 20 ended with a claim: the retail investor does not need a better put, they need a better default. The behavioral gap had eaten 73–96% of the garment's nominal protection, and the binding constraint was the wearer, not the contract. Panic sells, lapses, and cash raids — the garment falls off exactly when the tail arrives.

So the design question is unavoidable: what is a *better default* actually worth? Is it a free lunch, a cheap lunch, or a trap? And — the question nobody asks — does it have a shape? Does half a commitment buy half the protection, or does the value hide somewhere unexpected?

This part prices it. The answer is uncomfortable: on tail metrics, commitment is **all-or-nothing**. The first three quarters of a commitment buy almost nothing. The last quarter buys almost everything. And the reason is not the cost — it is the mathematics of the worst 1%.

## The machine

We reuse the machinery of Parts 19 and 20 exactly. The market shocks are the same (P4/P6 losses, seed 20260921, 2,000 paths per level). The garments are the same: the put (20% deductible, 2% premium, hard cap at −22%) and the cash buffer (20%, geometric scaling). The behavioral failures are the same: panic selling (40% of deep paths, locking −28%), lapsed renewal (40%, back to bare), cash raids (25%, back to bare).

The new parameter is **commitment strength** `c ∈ [0,1]`:

- `c = 0` — the naive investor of Part 20. Every behavioral failure fires at full force.
- `c = 1` — the mechanical garment of Part 19. Standing renewal, separate accounts, written rules: zero behavioral failure.
- Between the extremes, commitment is a **rescue layer**: the same shocks, the same impulses occur, and each failed path is rescued back to the mechanical outcome with probability `c`.

By construction, `c = 0` reproduces Part 20's published numbers exactly, and `c = 1` (gross of cost) reproduces Part 19's mechanical numbers. Every path improves monotonically in `c`. Commitment is not free: it costs a fraction of assets per year, `0.5%` per full unit in the cheap scenario, `2%` in the expensive one.

## The anchor: real commitment devices are absurdly cheap

Before the numbers, the field evidence — because it frames what "commitment costs" should mean.

**Save More Tomorrow** (Thaler & Benartzi, *Journal of Political Economy*, 2004): employees were offered a plan that commits a *portion of future raises* to savings automatically. 78% of those offered joined. 80% stayed through four pay raises. Average savings rates rose from 3.5% to 11.6% in 28 months (13.6% over 40 months in the JPE sample). No pain, no lapse — because the commitment was executed before the money ever arrived.

**401(k) automatic enrollment** (Madrian & Shea, 2001): the same company, the same plan, one change — the default flipped from "not enrolled unless you opt in" to "enrolled unless you opt out." Participation among new employees jumped from roughly 40% to 86%. A default option is free. It moved 46 points of participation.

And the caution from Choi et al.: automatic enrollees mostly *stay* at the default 3% contribution rate. The default is powerful precisely because it is sticky — which is why designing the default well matters. Commitment devices work; what they are committed *to* is the design question.

The common thread: **these interventions cost almost nothing and move behavior massively**. That maps onto our model as the cost line — and the model's answer is blunt: cost is not the constraint. The constraint is whether you commit at all, and how far.

## Finding 1 — commitment is all-or-nothing

Gross behavioral put p1 (worst 1% loss) per commitment level:

| C | c=0 | c=0.25 | c=0.50 | c=0.75 | c=1.00 |
|---|---|---|---|---|---|
| 1.00 | −28.5% | −28.3% | −28.0% | −28.0% | **−22.0%** |
| 0.75 | −52.2% | −52.0% | −49.9% | −46.2% | **−22.0%** |
| 0.50 | −58.0% | −57.1% | −55.7% | −53.7% | **−22.0%** |
| 0.25 | −61.9% | −61.3% | −60.7% | −58.6% | **−22.0%** |
| 0.00 | −42.4% | −41.8% | −41.3% | −39.7% | **−22.0%** |

*Mechanism: Part 19/20 machinery, seed 20260921, 2,000 paths/level. C = market's belief in backstop capacity; c = commitment strength.*

Now the marginal value — the points of p1 improvement each quarter of commitment buys:

| C | c: 0→.25 | .25→.5 | .5→.75 | .75→1 | total |
|---|---|---|---|---|---|
| 1.00 | 0.2 | 0.3 | 0.0 | **6.0** | 6.5 |
| 0.75 | 0.2 | 2.0 | 3.7 | **24.2** | 30.2 |
| 0.50 | 0.9 | 1.4 | 2.0 | **31.7** | 36.0 |
| 0.25 | 0.6 | 0.6 | 2.1 | **36.6** | 39.9 |
| 0.00 | 0.5 | 0.5 | 1.6 | **17.7** | 20.3 |

Read the C=0.25 row. The first 75% of commitment — rescue three out of four behavioral failures — buys 3.3 points (−61.9% → −58.6%). The last 25% buys **36.6 points**. Nine-tenths of the entire protection of commitment lives in the final quarter.

Why? Because p1 is the worst 1% — an extreme-order statistic. As long as *any* behavioral failure survives, the worst paths are deep losses: a single un-rescued panic locks −28%; a single lapse returns the investor to bare, where the tail is −60% territory. At `c = 0.75`, 25% of failures still fire — and with hundreds of failed paths, the worst 1% is almost guaranteed to be one of them. The tail only pins once the rescue rate is near 1. The mechanical cap of −22% is the "all"; the behavioral tail is the "nothing"; between them there is almost no transition.

Intuition says half a commitment buys half the protection. The tail says: half a commitment is a waste of half a commitment. On p1, commitment is binary.

(The cash garment shows the same shape, muted: in the depleted world, the first 0.75 of commitment buys 3.1 points, the last 0.25 buys 7.7 points.)

## Finding 2 — cost is not the constraint

Net p1 with commitment cost — including the expensive 2%/yr scenario:

| C | bare p1 | net put p1 @ c\*=1.00 (2% cost) | improvement |
|---|---|---|---|
| 1.00 | −29.4% | −24.0% | 5.4 pts |
| 0.75 | −55.9% | −24.0% | 31.9 pts |
| 0.50 | −61.3% | −24.0% | 37.3 pts |
| 0.25 | −63.7% | −24.0% | 39.7 pts |
| 0.00 | −44.1% | −24.0% | 20.1 pts |

The optimal commitment strength `c*` is **1.00 in every world, at both costs**. Not 0.90, not 0.75 — full. Even the expensive scenario (2%/yr) cannot dent full commitment, because the last quarter alone delivers 6–37 points of protection against at most 0.5 points of extra cost.

This is the model's version of the 401(k) finding: the default flip costs nothing and moves 46 points. Commitment devices are not priced like options or insurance — they are priced like *software settings*. The binding constraint was never money. It is the decision to automate at all — and the discipline to automate *fully*.

## Finding 3 — the value of commitment scales with capacity drain

The improvement column above is the story: in the calm world (C=1.00), full commitment buys 5.4 points net. In the depleted world (C=0.25) — where the market half-believes the backstop and leverage is at its highest — it buys **39.7 points**, 7.3× more.

Same mechanism as Part 19's put-vs-cash gap: the deeper the tail, the more the mechanical execution matters, because the deeper the tail, the more behavioral failure costs. The garment is worth the most exactly when the policy clock is most drained — when the investor is most tempted to improvise. Commitment is cheap insurance against improvisation, and improvisation is most dangerous precisely when the backstop is least credible.

## What the retail investor should actually do

1. **Never buy half a commitment.** Automatic renewal, panic-lock rules, and separate accounts go together. Three out of four is worth 3 points in the worst world; four out of four is worth 40. The tail punishes partial automation with disproportionate cruelty.

2. **Do not bargain over the cost of the commitment device.** At any plausible price, full commitment wins. The expensive scenarios in this model were still dominated by the last quarter of protection. The question is not "can I afford it" — it is "will I let it run."

3. **Put the commitment where the improvisation is.** The biggest behavioral channel in every world is panic selling (the failure that *deepens* losses beyond the mechanical cap). The second is lapse (returning to bare). A default that auto-renews and auto-executes is worth more than a cleverer contract — this is the 401(k) lesson restated: the default *is* the policy.

4. **Design the default, don't just flip it.** Choi et al.'s caution applies: automatic enrollees stay at the default 3%. A commitment device that automates the wrong level (too little buffer, too high a deductible, renewal priced at the wrong moment) locks in the wrong answer with the same sticky power. The stickiness is the product; get the default right before you make it automatic.

## The next hole

The garment now has all four layers: the mechanism (Part 19), the behavior (Part 20), the commitment (this part), and the cost (this part). But commitment has a weakness the model cannot price — the wearer who exempts themselves. "This time it's different." The self-exemption loophole, and what it does to the all-or-nothing curve, is the next part.

---

*Code: `crash_simulator_v10/commitment_device.py` (V10-P9), rescue-layer commitment model, self-test and Monte Carlo included. Deterministic, 281 lines, no dependencies beyond the standard library.*

*Drafted with AI assistance; facts, figures, and errors are the author's own.*

*Currently available for freelance work — Python pipelines, quantitative risk tooling, and AI data automation. Reach me at gopipibank@gmail.com.*
