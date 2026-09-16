# System Dynamics: When the Crash Becomes Its Own Engine

**In early September 2026, the VIX sat near its five-year calm, while the SKEW index sat near its high — a market both quiet and terrified. That contradiction was the subject of my last article. This one is about something more dangerous than expensive tail insurance: what happens when leverage is hiding in a calm market. Because a crash with leverage isn't an event. It's an engine that runs on its own fuel.**

---

The mechanism is simple, and it has ended markets twice in living memory (2008, March 2020):

1. Prices fall 5%.
2. Margin accounts are suddenly under water.
3. Brokers force liquidation.
4. Forced selling pushes prices down another 5%.
5. More accounts go under. Repeat.

This is the **margin spiral**, a positive feedback loop. And here is the thing that separates it from everything a classical risk model knows how to handle: **in a spiral, the fall is not caused by news. The fall is caused by the previous fall.** The market becomes its own shock.

## Why classical risk models are blind to this

A standard VaR model lives in a one-way world:

```
news / rates / earnings  →  price moves  →  portfolio losses
```

The market hits you, you compute the damage. Clean, exogenous, one direction.

The spiral lives in a different world:

```
price falls  →  margin calls  →  forced selling  →  price falls more
```

The direction is reversed — and it loops. **You don't just receive the market shock; your own leverage creates it.** Dean Lee, a reader with deep derivatives knowledge, pushed back on my first article with exactly this point:

> "In property insurance, a hurricane doesn't read the policy book. In capital markets, the hazard layer is created by the financial contracts themselves."

He was right, and this is the piece of my framework that answers him: **the hazard layer must model the contracts, not just the events.**

## The insurance analogy, sharpened

Insurers price hurricanes. A hurricane is exogenous — it doesn't get stronger because more people bought coastal policies. That assumption makes the four-layer catastrophe model clean and tractable.

A crash is different. A crash **does** get deeper because more people bought leverage. The more margin debt in the system, the more fuel the spiral has:

- A 10% drop in a low-leverage market is a correction.
- The same 10% drop in a highly-leveraged market triggers liquidations that turn it into 30%.

This is the **endogeneity** that property insurance never faces and financial risk modeling cannot ignore. The hazard is a function of the state of the system — including the positions of everyone in it.

## Modeling the loop

A feedback loop is not a probability distribution. It's a **differential equation with a sign wrong on purpose** — you model the iteration, not the event.

In `src/system_dynamics.py` of my open-source Crash Simulator, the spiral is modeled as a stock-and-flow loop:

```
state at time t:
  price, margin-debt stock, margin threshold, forced-selling flow

iteration t → t+1:
  price drop      → equity falls below threshold
  threshold breach → forced selling flow activates
  selling flow     → price drops further
```

Each iteration feeds the next — the loop keeps running until one of two things happens: the system de-leverages (selling exhausts the weak hands), or an external actor intervenes.

That last point matters. **The 2020 and 2008 rescues were not about "fixing the news."** They were about breaking the loop — central banks providing liquidity so forced selling stopped feeding price declines. When you model the crash as an event, intervention looks like a side story. When you model it as a loop, intervention *is* the story.

## Three things the spiral teaches

1. **Leverage is not volatility — it's the acceleration of downside.** Volatility tells you how big moves are. Leverage tells you how much a move will feed itself. A calm VIX says nothing about the leverage hiding underneath it.

2. **A crash is a process, not a point.** The EP curve tells you how much you lose; system dynamics tells you *why* you lose it — and why the same shock produces different outcomes depending on what the system looked like before.

3. **Intervention is a design input, not an afterthought.** If your model has no mechanism for "the loop gets broken," your tail scenarios are systematically overstated in the panic case — and understated in the forced-deleveraging case.

## What's next: the same logic, one level down

The same feedback logic lives at the microstructure level, in a form that's been in the news more than once: **dealer short gamma.** Options market-makers who sell volatility are forced to mechanically hedge — buying when markets rise, selling when they fall. In a selloff, their mechanical hedging becomes forced selling into a falling market, manufacturing the very tail event the model is trying to measure. Same loop, different actors.

That's the V9 direction I'm building next — extending the feedback layer from portfolio leverage to dealer hedging flows. Building in public has been paying off: the roadmap keeps getting sharper, and the comments have been better than the code.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)**

I write about fat tails, risk engineering, and AI automation at **Fat Tail Notes**. If you've lived through a liquidation spiral — or modeled one — I'd love to hear how you've thought about the endogeneity problem.

*Currently available for freelance work — AI data automation, Python pipelines, and quantitative risk tools. Reach me at gopipibank@gmail.com.*

---

*Built with Python, an open-source framework, and the uncomfortable realization that in markets, the model itself is part of the system it models.*

---

*This article was written with AI assistance and reviewed by the author.*
