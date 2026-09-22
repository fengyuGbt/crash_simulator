# Moral Hazard Is Not a Misconception — It's a Measurement Problem

*Fat Tail Notes · Part 16 · V10-P4 revisited*

Last week this series argued that a backstop builds the tail it truncates: once leveraged accounts believe the policy will cap their losses, leverage rises, and the same shock lands on bigger books. A real academic paper is now arguing the opposite — and it is not a blog post, it is IMF-published research. Gideon Bornstein and Guido Lorenzoni's *Moral Hazard Misconceptions: The Case of the Greenspan Put* (2018) makes the case that the fear of the Fed put is, in their words, a misconception: under optimal discretionary intervention, borrowing rises but overborrowing disappears, and ex-post intervention becomes a substitute for ex-ante regulation.

My first reaction after reading it was to concede. My second reaction was that this is not a dispute about who is right. It is a dispute about which moment of the loss distribution you are willing to optimize. And the third, most uncomfortable finding: our own Part 15 contained a data error in two of its mean figures. This post fixes that too, because if you want readers to trust your tail numbers, you correct your center numbers in public.

## 1. What the paper actually says

The model is a three-period economy with a levered agent (B) who holds the risky asset, financed by debt from a patient saver (A), with sticky prices and an aggregate-demand externality. The mechanism runs through the labor wedge: a larger debt stock worsens recessions because debt payments transfer resources from high-propensity borrowers to low-propensity lenders, dragging down output exactly when output is already too low.

The paper compares three monetary regimes:

- **Inertial**: the central bank sets the interest rate before seeing the shock. The shock is uninsured, the aggregate-demand externality is live, and there is *overborrowing* — a marginal welfare loss from debt (dW/dD < 0). This is the textbook case for macroprudential regulation.
- **Proactive**: the central bank sets rates state-by-state after seeing the shock. With log preferences, it can fully stabilize asset prices and output — the Greenspan put at maximum potency. Borrowing goes *up* (Proposition 2), but overborrowing goes to zero (Proposition 3): dW/dD = 0, so a borrowing tax buys nothing.
- **Output targeting**: commits to the flexible-price allocation; coincides with the proactive regime in the log case.

The headline: more borrowing, less overborrowing. The put does not create the inefficiency that regulation exists to fix, so ex-post intervention and ex-ante macroprudential policy are *substitutes*. Moral hazard as conventionally feared is a misconception.

## 2. The knife-edge they concede

The full-results version is narrower than the headline, and the paper says so itself. The perfect-stabilization result is a knife-edge that requires log utility — an elasticity of intertemporal substitution of exactly one, where income and substitution effects cancel. Section 5 shows what happens away from that edge: once preferences are general CRRA, the central bank faces a tradeoff between output stabilization and financial stability, and the insurance motive pushes it to stabilize asset prices *beyond* what output targeting requires.

That is the telling part. **In their own Section 5.2, the moment the central bank goes beyond output-gap targeting to prop up asset prices — the actual behavior people mean by "the put" — monetary policy and macroprudential policy become complements, and the optimal borrowing tax is *larger* in the proactive regime than in the output-targeting regime.** The conventional moral-hazard result comes back. What the paper really shows is not "moral hazard is a misconception" but "moral hazard disappears exactly on the log-utility knife-edge where the put is a perfect insurance contract."

There is a second, quieter assumption running through the whole paper: welfare is always evaluated as *expected* utility, E[V^A + βV^B]. Every proposition is about the mean of the welfare distribution. Nothing in the model — not one equation — looks at the lower tail of the outcome distribution as a separate object.

## 3. What our code says, on both accounts

Here is the trap we built to show. Our Monte Carlo (2,000 paths, seed 20260921) lets leverage be either exogenous (λ = 1.0) or policy-endogenous (λ drawn from a distribution with mean above 1 — the world the backstop creates). The same 2,000 shocks, two different worlds:

| scenario | mean | p10 | p1 | worst |
|---|---|---|---|---|
| no backstop, λ=1.0 (exogenous) | -34.1% | -41.0% | -43.9% | -49.0% |
| backstop, λ=1.0 (exogenous) | -21.3% | -23.2% | -24.8% | -31.1% |
| backstop, λ ~ N(1.35, 0.25) | -24.5% | -27.5% | -29.4% | -31.3% |
| backstop, λ ~ N(1.5, 0.30) | -25.5% | -28.4% | -30.4% | -31.7% |
| backstop, λ ~ N(1.75, 0.35) | -26.9% | -29.5% | -31.1% | -33.2% |

Now read the same table through each paper's lens.

**Bornstein-Lorenzoni's lens — the mean.** The backstop rescues the mean by 12.8 points (-34.1% → -21.3%). Endogenous leverage eats 5.6 of those points back (-21.3% → -26.9% at λ~1.75), 44% of the mean rescue. By a mean-welfare standard, the policy is doing its job: it improves the average outcome massively, and the erosion, while real, is a second-order correction to a first-order rescue.

**Our lens — the tail.** The backstop's p1 rescue is 19.1 points (-43.9% → -24.8%) — the tail is where the policy's value is concentrated. Endogenous leverage eats 6.3 points of that tail (-24.8% → -31.1%), 33% of the p1 rescue, and shifts p10 from -23.2% to -29.5%. The rescue is not canceled, but the deepest outcomes the policy promises to prevent are precisely the ones drifting back toward the no-policy world.

Same shocks, same policy, two defensible accounts. The disagreement is not in the mechanism — both accounts agree leverage responds to the put. The disagreement is in the objective function: **expected welfare has no tail. Tail risk has no average.**

## 4. Which measure is right? It depends on the cost of the tail.

Here is the honest version of the argument. If the social cost of a crisis is proportional to the mean loss, Bornstein and Lorenzoni are right — the backstop is a clean win and the moral-hazard complaint is a distraction. But crisis costs are not proportional. A -25% drawdown and a -31% drawdown do not cost society in the same units: the second one crosses into forced selling cascades, dealer gamma flips, liquidity gaps, policy-space exhaustion, and the political aftershocks that turn a market event into a regulatory one. The cost function is convex in the loss, and convexity is exactly what expected utility with representative agents averages away.

Two doctors see the same patient. Doctor A prescribes the painkiller because mean pain over the year falls from 7 to 4. Doctor B objects that the worst day — the day the patient overexerts because the painkiller masks the injury — went from 9 to 10. Both are reporting the same data. The patient's choice is which number the treatment is supposed to optimize. A central bank that only reports the mean is Doctor A reporting only the mean.

## 5. Their paper actually licenses our setup

The most useful sentence in *Moral Hazard Misconceptions* is the one that limits its own headline: complementarity — the return of moral hazard — appears "if the monetary authority goes over and above a simple objective of reducing the output gap." Our Part 12-15 series models exactly that kind of intervention: a *backstop*, an explicit asset-price floor and liquidity guarantee, not a Taylor rule. We are not on their log-utility knife-edge where the put is a perfect insurance contract; we are in the regime their Section 5.2 shows to be the complementary one, where the put stabilizes asset prices beyond output targeting and the borrowing tax is *more* valuable, not less.

Which is why the two literatures converge on the same policy conclusion from opposite directions. Boissay and Uhlig's *Reserves and the Buyer of Last Resort* (NBER w35548) calls it the market-backstop principle: make the backstop state-contingent and pair it with liquidity requirements that tax the behavior the backstop insures. Our Part 15 ended at the same place by simulation: ambiguity stops the front-run, but only a leverage rule stops the subsidy.

## 6. Correction and judgment

**Correction.** In the Part 15 Monte Carlo table, two mean figures were wrong: the no-backstop mean should be -34.1% (published as -42.3%) and the exogenous-backstop mean should be -21.3% (published as -24.6%). All p10, p1, and worst figures were correct. The corrected means change one sentence of that post's argument: the mean does move under endogenous leverage (-21.3% → -24.5% → -25.5% → -26.9%), it just moves less than the tail, and the rescue's value is concentrated in the tail either way. The stronger, corrected claim: **the backstop's value lives in the tail, and the tail is also where the leverage it induces does the most damage.**

**Judgment.** For the retail investor, the academic argument over moral hazard is not the thing to resolve. Two facts survive it. First, in mean terms, interventions do hold the market up — the rescue is real, and betting against it is a fool's trade. Second, in tail terms, the same intervention is accumulating the leverage that will make the next floor deeper — the rescue is expensive, and it is priced in the distribution's tail, not its headline. A put is not permission to be naked; it is time to put on the underwear.

---

*Code: `crash_simulator_v10/policy_moral_hazard.py` (V10-P4), self-test and Monte Carlo included. Deterministic, 402 lines, no external dependencies. Correction committed alongside this post.*

*Paper: Bornstein & Lorenzoni, "Moral Hazard Misconceptions: The Case of the Greenspan Put" — gideon-bornstein.com/papers/Moral_Hazard_Greenspan_Put.pdf*

*Available for freelance work — Python pipelines, quantitative risk tooling, AI data automation. Reach me at gopipibank@gmail.com.*

*Drafted with AI assistance; facts, figures, and errors are the author's own.*
