# The Leverage Subsidy: When the Backstop Builds the Tail It Truncates

*Fat Tail Notes · Part 15 · V10-P4*

Part 14 showed that a transparent backstop gets front-run, and that a
little noise — constructive ambiguity — breaks the front-run's aim. Part
14 ended by asking what happens when the market learns that the rule is
fuzzy. The answer this module gives is more uncomfortable than the
question: **the market does not have to learn the rule at all. It only
has to learn that a backstop exists.**

If leveraged accounts believe the policy will cap their losses, the
equilibrium level of leverage rises. The same shock lands on bigger
books with thinner margins. The tail the policy is trying to truncate is
the tail it helped build. This is the Greenspan/Fed put debate, reduced
to a kernel and measured.

## 1. The mechanism: leverage as a policy-endogenous variable

V10-P4 scales the four margin buckets by a leverage multiplier λ, in two
ways that both have real-world meaning:

- **bigger books**: every bucket's notional weight is multiplied by λ —
  the same positions, more of them;
- **thinner margins**: every bucket's trip threshold is divided by λ —
  higher leverage means the same drawdown trips the position earlier.

λ = 1.0 is the exogenous world: today's leverage, whatever it is, taken
as given. λ > 1.0 is the world the backstop itself creates: once the
market believes in the put, books grow and margins thin.

On the calibration path the mechanism is clean:

| λ (leverage) | no backstop | backstop | backstop saves |
|---|---|---|---|
| 1.0 | -36.5% | **-22.8%** | 13.7 pts |
| 1.5 | -46.0% | **-27.6%** | 18.4 pts |
| 2.0 | -54.1% | **-29.1%** | 25.0 pts |

Read the backstop column vertically. The same policy, with the leverage
it induces, truncates a **deeper** tail every time: -22.8% → -27.6% →
-29.1%. The backstop still helps — it helps a lot — but **the hole it
arrives at is a hole it dug**. The higher the leverage the backstop
subsidizes, the deeper the tail it has to catch.

## 2. The structural error in the standard stress test

Here is the trap. The standard way to stress-test a backstop is:

1. take today's observed leverage as given (λ = 1.0);
2. simulate the no-backstop counterfactual with that same leverage;
3. report the difference as "the value of the backstop."

But that is an **inconsistent world**. Today's leverage is not exogenous:
it already contains the backstop's promise. If the policy works, λ = 1.0
is the wrong input for both columns — too low for the with-backstop
column (the backstop grew the books) and too high for the no-backstop
column (without the put, the books would have been smaller). The
standard test is optimistic by construction.

Monte Carlo (2,000 paths, seed 20260921) makes the size of the error
explicit:

| scenario | mean | p10 | p1 | worst |
|---|---|---|---|---|
| no backstop, λ=1.0 (exogenous) | -42.3% | -41.0% | **-43.9%** | -49.0% |
| backstop, λ=1.0 (exogenous) | -24.6% | -23.2% | **-24.8%** | -31.1% |
| backstop, λ ~ N(1.35, 0.25) | -24.5% | -27.5% | **-29.4%** | -31.3% |
| backstop, λ ~ N(1.5, 0.30) | -25.5% | -28.4% | **-30.4%** | -31.7% |
| backstop, λ ~ N(1.75, 0.35) | -26.9% | -29.5% | **-31.1%** | -33.2% |

The p1 column tells the whole story. On the exogenous assumption the
backstop's p1 is -24.8% — a 19-point rescue from the -43.9% no-backstop
world. Once leverage is allowed to respond, the rescue shrinks: **-29.4%
at λ ~ 1.35 (24% of the rescue eaten), -31.1% at λ ~ 1.75 (33% eaten).**
The mean barely moves (-24.6% → -24.5% → -26.9%) because the backstop
compresses averages hard; **moral hazard bites the tail, not the mean.**

## 3. The p10 column: where the systematic optimism lives

The p10 comparison is the most uncomfortable for a risk modeler, because
it is the part of the tail they quote most:

| scenario | p10 |
|---|---|
| backstop, λ=1.0 (exogenous) | **-23.2%** |
| backstop, λ ~ N(1.35, 0.25) | **-27.5%** |
| backstop, λ ~ N(1.75, 0.35) | **-29.5%** |

An exogenous-leverage model reports -23.2% as the 10th percentile of the
post-policy world. A model that lets the policy act on leverage reports
-27.5% to -29.5% for the same percentile. **Four to six points of tail
are invisible when leverage is treated as a given.** That is not a
parameter error; it is a model-structure error.

## 4. What this means

Three claims, kernel-backed:

1. **The backstop is a leverage subsidy.** The promise that losses will
   be capped is an input to the leverage decision. The equilibrium tail
   is endogenous to the policy, and it is deeper than the policy's own
   headline number.
2. **Stress tests that hold leverage fixed are optimistic by
   construction.** They understate the with-policy tail (books grew) and
   overstate the no-policy counterfactual (books would have shrunk). The
   honest comparison is policy → leverage → tail, not policy | leverage
   → tail.
3. **Moral hazard bites the tail, not the mean.** If you only report
   expected shortfall at the center of the distribution, the feedback
   loop is invisible. It lives at p10 and below — exactly where tail
   risk is supposed to be measured.

The uncomfortable policy corollary: if the backstop pays for the
leverage that builds the tail, then the policy's optimal partner is not
more ambiguity — it is **directly taxing the leverage**: margin
requirements, position limits, a counter-cyclical capital charge on the
very books the put insures. Ambiguity stops the front-run; only a
leverage rule stops the subsidy.

The next iteration has a candidate: **what a margin rule does to the
equilibrium** — whether a counter-cyclical margin charge can recover the
rescued tail without killing the rescue. That is a policy instrument the
market cannot front-run and cannot leverage against.

---

*Code: `crash_simulator_v10/policy_moral_hazard.py` (V10-P4), self-test and Monte Carlo included. Deterministic, 402 lines, no dependencies beyond the standard library.*

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

*This article was written with AI assistance and reviewed by the author.*
