# When the Market Learns the Rule: Front-Running the Backstop

*Fat Tail Notes · Part 14 · V10-P3*

Part 13 made the backstop endogenous: it fires on state (2 tripped buckets AND a 20% drawdown), not on a calendar, and the announcement cuts unfinished sell intentions before they become liquidation. Part 13 ended with a warning dressed as a teaser: *what happens when the market learns the rule?*

This is that article. The answer is uncomfortable: **a transparent backstop is a front-running target.** If leveraged accounts know the trigger, the rational move is to pre-empt the liquidation — to sell *shallower* than the policy's line, because once the backstop fires the market rebounds, and the forced seller is left selling into the recovery. The policy listens to the market; so does the market listen to the policy.

## 1. The mechanism: front-running is just early tripping

In V10-P2 an unfired bucket trips when the drawdown crosses its margin threshold. V10-P3 adds one line of behavior for the market: **if the backstop rule is known, an unfired bucket trips on its own once the drawdown crosses the *anticipation* line — shallower than the policy's trigger.**

```
front-running starts  when  drawdown <= -anticipation_trigger   (e.g. -15%)
policy fires          when  drawdown <= -trigger_drawdown        (e.g. -20%)
```

The front-runner's sales are flow like any other — the price does not know whether the seller is forced or scared. Two consequences follow mechanically:

- the cascade starts earlier and runs faster, so the backstop arrives at a **deeper hole**;
- buckets that front-run have blown up before fire time, so the **expectations channel has fewer intentions left to cut** — the very channel that made the unbounded commitment work in Part 13 is drained from underneath.

On the calibration path the accounting is stark:

| scenario | total return | fire step | expected flow saved |
|---|---|---|---|
| no backstop | **-36.5%** | — | 0 |
| P2: market has not learned | **-22.8%** | 14 | 0.277 |
| P3: market learned the rule | **-24.7%** | 13 | 0.259 |

The rule costs **1.9 points of the tail** — and it costs it precisely through the channel Part 13 built: the expectations channel saves 0.277 of flow when the rule is private, only 0.259 when the rule is public. **The clearer the promise, the less it is worth.**

## 2. The paradox of forward guidance

This is the paradox every central bank lives with. A precisely communicated rule ("two buckets, twenty percent, no ceiling") is the most *priced* commitment in the market: everyone aims at the line, everyone pre-empts it. Guidance is supposed to anchor expectations. But an anchor that everyone can see is also an anchor everyone can pull against.

2020 is the counterfactual that proves the point: the Fed did **not** pre-announce "2 buckets and -20%." The 3/23 announcement was a *regime* announcement — "as needed, no limit" — whose trigger was not a published threshold but a judgment call. The market could not front-run a judgment it could not locate.

Which raises the policy question: **can ambiguity be engineered?**

## 3. Ambiguity is a knob, not a flaw

V10-P3 makes the trigger fuzzy: the policy fires at `trigger_drawdown + noise`, where the noise is symmetric (same expectation, unpredictable realization). The market cannot aim at a moving line, so front-running dies. But the noise has a cost — sometimes the policy fires late. Scan the noise size (Monte Carlo, 500 paths, seed 20260920):

| trigger noise | mean | p10 | p1 | worst |
|---|---|---|---|---|
| P2 base (no front-run) | -21.2% | -23.2% | -24.2% | -27.7% |
| 0% (transparent, front-run) | **-22.6%** | -24.9% | -25.5% | -27.9% |
| **2%** | **-21.4%** | -24.5% | -26.1% | -26.4% |
| 4% | -21.5% | -26.4% | -27.8% | -28.4% |
| 8% | -21.7% | -29.8% | -31.5% | -32.7% |
| 12% | -22.0% | -32.5% | -34.8% | -36.8% |

Two curves, one message. **Mean recovers as soon as the rule is fuzzy at all** — the front-run loses its aim. But the tail deteriorates monotonically with the noise: at 12% noise the p1 is -34.8%, essentially no backstop at all. The policy pays for ambiguity in trigger reliability.

The optimum is small: **about 2%.** Enough noise to break the front-run's aim, little enough to keep the trigger sharp. At 2% the mean is back to -21.4% (1.2 points recovered), and the worst case improves to -26.4% (1.5 points better than the transparent rule) — a free lunch, almost.

## 4. The distribution: what 2% buys

Full Monte Carlo (2,000 paths, seed 20260920):

| configuration | mean | p50 | p10 | p1 | worst |
|---|---|---|---|---|---|
| P2: not learned | -21.2% | -22.4% | -23.2% | -25.0% | -30.8% |
| P3: rule learned | -22.6% | -24.0% | -24.9% | -25.6% | -31.0% |
| P3 + 2% fuzzy | **-21.4%** | **-22.4%** | -24.4% | -25.8% | **-28.7%** |

Read the edges. A learned rule costs **1.5 points of mean and 2.3 points of worst case** vs the not-learned world — that is the price of transparency. A 2% fuzz buys back 1.2 points of mean and **2.3 points of worst case**. The only residual cost is a hair on the p1 (-25.8% vs -25.6%) — the occasional late trigger, the honest price of ambiguity.

## 5. What this means

Three claims, kernel-backed:

1. **Endogenous policy meets endogenous markets.** The same reflex that makes the backstop listen to the market makes the market listen to the backstop. A rule that cannot be hidden will be aimed at.
2. **Constructive ambiguity is not a weakness of central banks — it is a policy tool.** The "I can't tell you the exact trigger" posture is not vagueness; it is the mechanism that stops the front-run. 2020's bottom happened not because the rule was clear but because it could not be located.
3. **Ambiguity is a knob, and it has an optimum.** Too transparent, and the market front-runs you. Too fuzzy, and you fire late into worse holes. The scan says the operating point is narrow — a few points of noise, enough to break the aim, not enough to break the trigger.

The next iteration has a candidate already: **what happens when the market learns that the rule is fuzzy** — when the front-runner becomes an *adaptive* learner, estimating the noise and aiming at its expectation. The game of endogenous policy does not end; it escalates.

---

*Code: `crash_simulator_v10/policy_anticipation.py` (V10-P3), self-test and Monte Carlo included. Deterministic, 438 lines, no dependencies beyond the standard library.*

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

*This article was written with AI assistance and reviewed by the author.*
