# The Behavioral Gap: What Protection Actually Delivers After Panic, Lapse, and Raids

*Fat Tail Notes · Part 20 · V10-P8*

Part 19 priced the retail garment and found something encouraging: a 2% cash buffer and a 2% put both improve the tail at every policy-capacity level, and at C=0.25 the put's nominal tail protection reaches 41.7 points. Then Part 19 ended with the uncomfortable question this part answers with numbers: the garments are mechanical in the model, but they are worn by people. What does the protection actually deliver once panic selling, lapsed renewals, and raided cash buffers are priced in?

The answer is stark. **The behavioral gap eats 73% to 96% of nominal protection.** At C=0.25, the put that nominally saves 41.7 points on the 1st percentile actually saves 1.8 points once people are in the model. The underwear works on paper and falls off in practice.

## 1. What the crisis does to retail behavior

The 2020 evidence is the anchor:

- The S&P 500 fell 34% in 33 days through March 23, 2020, with single-day drops of 9.5% and 12.9%.
- Vanguard's study of its US retail investors (2/19–5/31): only 17% traded at all, and fewer than 0.5% panic-liquidated everything. The garment mostly stayed on — but the minority who took it off did so at the worst moment, and lagged in the rebound.
- The Indian market tells the other side: SEBI data show retail investors withdrew about ₹25,000 crore from equity mutual funds in March–May 2020 — just before an 80% rebound. The ones who sold locked their losses and missed the recovery.
- The behavior literature is old and consistent: loss aversion (Kahneman & Tversky) makes losses feel about 2-2.5x as bad as equal gains; the disposition effect (Shefrin & Statman) makes investors sell winners early and ride losers down. Panic selling is the tail of those biases.

And the experience literature explains who wears the garment: Malmendier & Nagel's Depression Babies (QJE 2011) show that people who have lived through big crashes shy away from stocks for years or decades — lower participation, lower equity share. The first-time investor who has never seen a bear market is exactly the person who panics first.

## 2. The model: three failure channels, one behavioral clock

We reuse the market-loss machinery of Parts 15-19 (P4's `run_policy_moral_hazard`, P6's capacity levels, P7's garments). On top of the mechanical garments we add three behavioral failure channels, each triggered by the crisis itself (seed 20260921, 2,000 paths per level):

- **Panic sell** — when a path passes -25%, the investor sells and locks a realized loss at -28% (three points of panic slippage), with probability 40%. The option garment's hard cap softens from -22% to -28%, and the garment is gone for that path.
- **Lapse** — the option renewal, repriced at crisis cost (Part 19's 6% world), is not paid with probability 40%. The put garment vanishes and the path reverts to bare.
- **Cash raid** — the cash buffer is spent under stress with probability 25%. The cash garment vanishes and the path reverts to bare.

An experienced investor — who has lived through a crisis — has failure rates roughly halved (Malmendier & Nagel in reverse). The question is how much that experience is worth in tail space.

## 3. The behavioral gap: nominal vs actual protection

Full table (per policy capacity C; bare = no garment, mech = Part 19's numbers, bhv = behavioral):

| C | garment | mean | p10 | p1 | worst | >30% |
|---|---|---|---|---|---|---|
| 1.00 | bare | -24.6% | -27.6% | -29.4% | -31.5% | 0.4% |
| 1.00 | mech cash | -19.7% | -22.1% | -23.5% | -25.2% | 0.0% |
| 1.00 | bhv cash | -20.9% | -25.4% | **-28.0%** | -30.2% | 0.1% |
| 1.00 | mech put | -21.5% | -22.0% | -22.0% | -22.0% | 0.0% |
| 1.00 | bhv put | -23.6% | -28.0% | **-28.5%** | -30.3% | 0.1% |
| 0.75 | bare | -30.7% | -47.8% | -55.9% | -61.6% | 27.2% |
| 0.75 | mech cash | -24.5% | -38.3% | -44.7% | -49.3% | 23.9% |
| 0.75 | bhv cash | -26.1% | -40.3% | **-52.9%** | -60.8% | 24.9% |
| 0.75 | mech put | -21.6% | -22.0% | -22.0% | -22.0% | 0.0% |
| 0.75 | bhv put | -25.7% | -28.0% | **-52.2%** | -58.1% | 7.1% |
| 0.50 | bare | -38.6% | -55.4% | -61.3% | -66.1% | 54.9% |
| 0.50 | mech cash | -30.8% | -44.3% | -49.0% | -52.9% | 49.2% |
| 0.50 | bhv cash | -32.8% | -48.1% | **-58.1%** | -64.4% | 50.6% |
| 0.50 | mech put | -21.8% | -22.0% | -22.0% | -22.0% | 0.0% |
| 0.50 | bhv put | -27.9% | -44.2% | **-58.0%** | -66.1% | 12.8% |
| 0.25 | bare | -47.1% | -60.5% | -63.7% | -66.1% | 80.5% |
| 0.25 | mech cash | -37.6% | -48.4% | -51.0% | -52.9% | 73.8% |
| 0.25 | bhv cash | -40.1% | -53.8% | **-61.7%** | -64.8% | 76.0% |
| 0.25 | mech put | -21.9% | -22.0% | -22.0% | -22.0% | 0.0% |
| 0.25 | bhv put | -30.1% | -53.2% | **-61.9%** | -66.1% | 18.8% |
| 0.00 | bare | -33.9% | -41.0% | -44.1% | -46.7% | 84.4% |
| 0.00 | mech cash | -27.1% | -32.8% | -35.3% | -37.3% | 38.9% |
| 0.00 | bhv cash | -28.9% | -37.8% | **-42.6%** | -46.5% | 50.6% |
| 0.00 | mech put | -20.7% | -22.0% | -22.0% | -22.0% | 0.0% |
| 0.00 | bhv put | -25.9% | -37.4% | **-42.4%** | -46.5% | 20.5% |

The mechanical column is Part 19. The behavioral column is the same instrument worn by people. The difference is the behavioral gap — and it is measured in points of tail protection.

## 4. The gap, in points

Nominal vs actual p1 improvement over bare:

| C | put: nominal | put: actual | cash: nominal | cash: actual |
|---|---|---|---|---|
| 1.00 | 7.4 pts | 0.9 pts | 5.9 pts | 1.4 pts |
| 0.75 | 33.9 pts | 3.7 pts | 11.2 pts | 3.0 pts |
| 0.50 | 39.3 pts | 3.3 pts | 12.3 pts | 3.2 pts |
| 0.25 | 41.7 pts | 1.8 pts | 12.7 pts | 2.0 pts |
| 0.00 | 22.1 pts | 1.8 pts | 8.8 pts | 1.6 pts |

Three readings from the numbers.

**First: the garment fails by disappearing, not by worsening.** Lapse and raid do not degrade the protection — they erase it, sending the path back to the bare distribution. Panic does not merely soften the cap; it replaces the garment with a realized loss. That is why the gap is so large: the worst paths in the behavioral distribution are not "protected but worse" paths, they are *unprotected* paths. The underwear either stays on or it is gone; there is no in-between. And the failures are the tail: panic share rises monotonically as capacity drains, from 20.5% of paths at C=1.00 to 38.2% at C=0.25 — 20.5% -> 38.2% of deep paths end in a panic sale exactly where the garment mattered most.

**Second: the behavioral clock runs in the same direction as the policy clock.** Part 18 showed the backstop is weakest when most needed. Part 20 shows the retail garment is most likely to fall off when most needed. At C=1.00 (calm world, shallow crises), panic triggers on 20.5% of paths and the behavioral put still keeps the tail near -28%. At C=0.25 (depleted backstop, deep crises), panic triggers on 38.2% of paths, lapses and raids push p1 back toward bare, and the put that nominally saves 41.7 points actually saves 1.8. The two clocks — policy capacity and behavioral discipline — run in the same direction, and both fail hardest in the same world.

**Third: experience is worth more in moderate crises than in extreme ones.** Halving the failure rates (the experienced investor) improves the behavioral put p1 by 0.5 pts at C=1.00, 3.4 pts at C=0.75, 0.2 pts at C=0.50, 0.7 pts at C=0.25, 0.8 pts at C=0.00. Experience is most valuable at C=0.75 — the moderate-crisis world where the garment still has a chance — and nearly useless at the extreme: at C=0.25 the tail is so deep that even halved failure rates leave enough lapsed and raided paths to dominate the 1st percentile. The Depression-babies effect is real, and it is a medium-crisis effect. In the extreme world, no amount of lived experience keeps the underwear on.

## 5. What the numbers say a retail investor should do

**The garment is necessary but not sufficient. The binding constraint is not the price of protection — it is the wearer.**

Three practical moves follow from the structure:

1. **Make the garment automatic.** Panic, lapse, and raid are all discretionary acts that the model prices as probabilities. Pre-commitment removes the discretion: automatic rolling puts with standing renewal instructions, cash in a separate account you cannot raid by reflex, a written rule ("I sell nothing in the first 72 hours after a -25% print") that exists before the panic does. The 2020 Vanguard number — under 0.5% of investors panic-liquidated — suggests most people keep the garment on; the ones who do not are the ones whose tail is unprotected, and automation is the cheapest way to move yourself out of that minority.

2. **Do not let the calm world fool you into a bigger tail.** The behavioral gap at C=1.00 looks small (0.9-1.4 pts saved), but C is not a constant: Part 18's clock reads policy capacity, and it drains. The gap is largest exactly where the garment is most needed. Price the protection for the C=0.25 world while the market still looks like C=1.00.

3. **Price your own experience honestly.** If you have never lived through a bear market, your failure rates are the naive column — the model says halving them buys 0.5-3.4 points of tail. The cheapest way to halve them is not more information; it is structure: written rules, automatic flows, and a garment that does not require you to make a good decision in the middle of a 9.5% down day.

## 6. Where this leaves the series

Part 18 priced the backstop's clock. Part 19 priced the garment. Part 20 priced the wearer. The series' four layers are now complete in one direction: the market's own protection is probabilistic (policy clock), the retail garment that must exist is priced (cash and puts, both ~2%/yr), and the garment's actual delivery is gated by behavior — 73-96% of nominal protection is eaten by panic, lapse, and raids, with the gap widest exactly where the tail is deepest.

The remaining question is the one the model cannot answer: the garment is an insurance contract, but wearing it is a commitment device. If the numbers say the binding constraint is behavior, then the product a retail investor actually needs is not a better put — it is a better default. That is the hook for Part 21.

---

*Code: `crash_simulator_v10/behavioral_underwear.py` (V10-P8), self-test and Monte Carlo included. Deterministic, stdlib only. Numbers above are exact output with seed 20260921, market losses from the P4/P6 machinery, garments from P7, behavioral failure rates: panic 40% (trigger -25%, lock -28%), lapse 40%, cash raid 25%, experienced = halved.*

*Behavioral anchors: March 2020 (S&P -34% in 33 days; Vanguard study — 17% traded, <0.5% panic-liquidated; India SEBI — ₹25,000 crore withdrawn Mar-May 2020 before an 80% rebound); Kahneman & Tversky loss aversion; Shefrin & Statman disposition effect; Malmendier & Nagel Depression Babies (QJE 2011, NBER w14813) and experience effects (NBER w29074).*

*Available for freelance work — Python pipelines, quantitative risk tooling, AI data automation. Reach me at gopipibank@gmail.com.*

*Drafted with AI assistance; facts, figures, and errors are the author's own.*
