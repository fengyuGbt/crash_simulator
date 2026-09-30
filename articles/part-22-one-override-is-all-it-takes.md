# One Override Is All It Takes: The Self-Exemption Loophole

*Part 22 of the Fat Tail Notes series — what "this time is different" costs the retail investor.*

## The hook

Part 21 priced the commitment device and found it all-or-nothing: full commitment pins the worst 1% at the mechanical cap, and the value lives in the last quarter. The design conclusion was blunt — never buy half a commitment.

But the device has a hole that no amount of commitment strength closes. The hole is the wearer. The same investor who signed the automatic rules can, at the moment of crisis, override them. "This time is different." "I can sell just this once." "I'll renew tomorrow." Reinhart and Rogoff spent eight centuries of crisis history documenting this exact sentence — the four most expensive words in the English language, as John Templeton put it.

This part prices the hole. The answer is the mirror image of Part 21's finding, and it is worse: to win, you need 100% commitment. To lose, you need a single override.

## The machine

We take the Part 21 setup and attack it. Full commitment (`c = 1`) is in place: every behavioral failure — panic selling, lapsed renewal, cash raid — is rescued back to the mechanical outcome. The market shocks are the same (P4/P6 losses, seed 20260921, 2,000 paths per level), the garments are the same (put: 20% deductible, 2% premium, −22% cap; cash: 20% buffer).

The new parameter is the **exemption rate** `e ∈ [0,1]`: the probability that, at the moment of crisis, the investor overrides the standing rule despite full commitment — lets the panic trade through, lets the renewal lapse, lets the raid happen.

- `e = 0` — full commitment holds: Part 19's mechanical garment.
- `e = 1` — every impulse overrides the rules: Part 20's naive investor.
- Between the extremes, exemption is a **hole in the rescue layer**: full commitment would rescue each failure; exemption flips a share `e` of those rescues back into failures.

By construction, `e = 0` reproduces Part 19's mechanical numbers exactly, and `e = 1` reproduces Part 20's naive numbers exactly. Every path worsens monotonically in `e`.

## The anchor: the loophole is real, documented, and human

**"This time is different."** Reinhart & Rogoff (*This Time Is Different: Eight Centuries of Financial Folly*, 2009) catalogued 66 countries and 800 years of crises, and the recurring pre-crisis belief was always the same: the old rules no longer apply, the boom is different. It never was. The syndrome is not confined to governments — it is how the retail investor talks himself out of his own rules at the exact moment they matter.

**Why the override is irresistible: present bias.** O'Donoghue & Rabin (1999, *American Economic Review*) formalized the mechanism: a present-biased self discounts the future sharply, so at the moment of crisis, the cost of *not* selling (holding through the pain) feels immediate while the benefit of the rule (a smaller worst case) feels distant. The naive self plans; the present self overrides. This is not a character flaw — it is the standard model of human time preference.

**The good news: friction works.** The most famous commitment product in the field, the SEED savings account in the Philippines (Ashraf, Karlan & Yin, *Quarterly Journal of Economics*, 2006), was explicitly *not* an ironclad lock: the saver could still access the money by going to the bank and completing the paperwork. That friction was the product. Twelve months later, clients offered the account had average balances **81% higher** than the control group — and those who actually opened the account saved **337% more**. The commitment worked precisely because the exemption was costly. The hole was there, but it was narrow.

That is the design question our numbers now answer: how narrow does the hole have to be?

## Finding 1 — the damage is nonlinear: a 10% exemption destroys 85% of the garment

Put p1 (worst 1% loss) per exemption rate, under full commitment:

| C | e=0 | e=.10 | e=.25 | e=.50 | e=1.00 | bare |
|---|---|---|---|---|---|---|
| 1.00 | −22.0% | −28.0% | −28.0% | −28.0% | −28.5% | −29.4% |
| 0.75 | −22.0% | −28.7% | −44.6% | −50.4% | −52.2% | −55.9% |
| 0.50 | −22.0% | −42.1% | −52.4% | −56.1% | −58.0% | −61.3% |
| 0.25 | −22.0% | **−56.2%** | −59.9% | −60.8% | −61.9% | −63.7% |
| 0.00 | −22.0% | −36.9% | −39.5% | −41.1% | −42.4% | −44.1% |

*Mechanism: Part 19/20/21 machinery, seed 20260921, 2,000 paths/level. C = market's belief in backstop capacity; e = exemption rate.*

Read the C=0.25 row. Full commitment pins the tail at −22.0%. An exemption rate of **10%** — the investor overrides the rules one time in ten — jumps the worst 1% to **−56.2%**. That is 85.5% of the garment's entire protection destroyed by one-tenth of a loophole.

Why? The same extreme-order logic that made commitment all-or-nothing in Part 21. p1 is the worst 1%: as long as *any* override can fire, the deepest paths are exposed to it, and with hundreds of failed paths in the depleted world, the worst 1% is almost guaranteed to include an override. The tail does not care that 90% of the time the rules hold. The tail is decided by the paths where they did not.

## Finding 2 — the asymmetry: win needs 100%, lose needs one

The damage table makes the asymmetry exact (points of p1 eaten by exemption, put):

| C | e=.10 | e=.25 | e=.50 | e=1.00 | total protection |
|---|---|---|---|---|---|
| 1.00 | 6.0 | 6.0 | 6.0 | 6.5 | 6.5 |
| 0.75 | 6.7 | 22.6 | 28.4 | 30.2 | 30.2 |
| 0.50 | 20.1 | 30.4 | 34.1 | 36.0 | 36.0 |
| 0.25 | **34.2** | 37.9 | 38.8 | 39.9 | 39.9 |
| 0.00 | 14.9 | 17.5 | 19.1 | 20.3 | 20.3 |

Share of protection destroyed:

| C | e=.10 | e=.25 | e=.50 |
|---|---|---|---|
| 1.00 | 92.7% | 92.7% | 92.7% |
| 0.75 | 22.1% | 74.8% | 94.0% |
| 0.50 | 55.7% | 84.4% | 94.7% |
| 0.25 | **85.5%** | 94.9% | 97.2% |
| 0.00 | 73.1% | 86.0% | 93.8% |

Pair this with Part 21's table: commitment of 0 → 0.75 bought 3.3 points in the depleted world; exemption of 0 → 0.10 destroys 34.2. The device is violently asymmetric. Building commitment is a grind — each additional quarter of automation buys diminishing tail improvement until the last one, which buys everything. Destroying it is trivial — one tenth of a loophole eats most of it. In engineering terms: the mechanism has a sharp reliability cliff. The rules must work 100% of the time; they are not graded, they are pass-fail.

## Finding 3 — the loophole widens exactly when it is most dangerous

The destruction share rises with capacity drain: 22.1% in the C=0.75 world, 55.7% in C=0.50, 85.5% in C=0.25 — and the absolute damage rises from 6.7 to 34.2 points. The calm world is the one exception (92.7% share, but only 6.0 points total): there, protection was small to begin with and the tail is dominated by a handful of paths, so any override saturates it.

The pattern is the series' recurring clock: the less credible the backstop, the deeper the tail, the more behavioral failure costs — and therefore the more a single exemption costs. The self-loophole is priced in the same currency as the policy clock. When the market half-believes the backstop (C=0.25), the investor's own "this time is different" is worth −34 points of worst-case loss. The exemption is cheapest to grant and most expensive to pay, exactly at the same moment.

## What the retail investor should actually do

1. **Make exemption expensive.** The SEED lesson, quantified: the product worked (+81% balances) because accessing the money required going to the bank. Design the escape hatch to have friction — a cooling-off period, a written reason, a second signature. Every hour of friction is points of p1.

2. **Do not install an "except this once" button.** Present bias peaks exactly at the moment of crisis — that is when the override is most tempting and most expensive. An easy override is not a feature, it is a −34 point feature.

3. **Move the exemption decision out of the present.** Write the exemption criteria in advance: "I may override the rule only if X, Y, Z are all true" — and make the list narrow and concrete. The sophisticated self of O'Donoghue-Rabin commits the naive self; the present self should have no discretionary authority.

4. **The extreme design exists: make the commitment unbreakable.** Ulysses did not leave himself an override — he told his crew to tie him tighter and ignore his orders. Some products do this structurally (irrevocable accounts, third-party co-signers). The model's verdict is clear: the value of the garment is 39.9 points, and it survives only while the hole stays shut.

## The next hole

The loophole can be narrowed, but the wearer remains the weakest layer. What happens when the exemption is not the investor's whim but the *policy's*? The backstop itself — the thing the market believes in — has its own "this time is different" moment. When the commitment that matters is the government's, and the override is political, the tail we have been measuring changes shape. That is the next part.

---

*Code: `crash_simulator_v10/self_exemption.py` (V10-P10), exemption-hole model on the Part 21 commitment layer, self-test and Monte Carlo included. Deterministic, 250 lines, no dependencies beyond the standard library.*

*Drafted with AI assistance; facts, figures, and errors are the author's own.*

*Currently available for freelance work — Python pipelines, quantitative risk tooling, and AI data automation. Reach me at gopipibank@gmail.com.*
