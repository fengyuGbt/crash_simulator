# I Built a Stock Market Crash Simulator Using Insurance Catastrophe Modeling

**Why your portfolio falls apart exactly when you need it most — and what hurricane pricing can teach us about it.**

---

March 2020. The S&P 500 lost 34% in 33 days. Bitcoin fell with it. Gold fell with it. Even the "defensive" dividend stocks fell with it. Every asset class that your portfolio theory told you was "uncorrelated" suddenly moved in perfect lockstep — down.

This is not a bug in the market. It's a feature of how markets behave in a crisis. And it's the exact moment that every standard risk model — the ones built on normal distributions — quietly goes blind.

I spent months building a tool that doesn't go blind. Here's what I learned along the way.

## The problem with normal distributions

Most portfolio risk tools assume returns follow a normal distribution. The math is elegant, the tails are thin, and the models are tractable. There's just one problem: **markets don't read the textbooks.**

In normal times, the correlation between asset classes sits somewhere around 0.3–0.6. In a crisis, it converges toward 1.0. Everything falls together. Your "diversified" portfolio suddenly behaves like a single concentrated bet.

Standard Value-at-Risk (VaR) models compute something like "the worst 1% of outcomes." But when the true distribution has fat tails — when the 1% event is far worse than any normal distribution would ever allow — that number is dangerously optimistic. The model tells you the bridge can hold. The bridge collapses.

## Where insurance comes in

I come from a manufacturing and quality-engineering background, where you learn early that the **unlikely event is the one that kills you**. A part that fails 0.1% of the time is fine — until it's the part holding an aircraft together.

Insurance companies solved this problem a long time ago. When an insurer prices a hurricane policy, they don't ask "what's the average hurricane damage?" They ask something far more specific:

1. **Hazard** — how do hurricanes actually happen? (frequency, intensity, path)
2. **Exposure** — what's in the path? (the houses, the people, the assets)
3. **Vulnerability** — how fragile is each thing to a given storm? (roof type, construction quality)
4. **Loss** — what's the dollar damage? (and the probability of exceeding any given loss level)

This is the **catastrophe model** — the four-layer framework that lets insurers price the unpriceable. The key move is separating *how disasters happen* from *what they destroy*. Financial crashes are disasters too. So I built the same framework for equity portfolios.

## The four layers

### Layer 1: Hazard — how crashes happen

I built a hazard layer that generates crash scenarios in three ways:

- **Six historical crashes**: 2008 financial crisis, 2020 COVID crash, the 2022 China-ADR meltdown, and three more. Real events, real magnitude, real sector patterns.
- **SDE jump-diffusion models**: crashes don't creep; they jump. A stochastic differential equation with a jump component captures both the slow drift of normal times and the violent jumps of crisis. I used the `yuima` R package to estimate the parameters from real market data.
- **System dynamics**: the hidden feedback loop. When leveraged players get margin-called, they're forced to sell. Forced selling drives prices down. Falling prices trigger more margin calls. This loop — not "the news" — is what turns a correction into a crash. I modeled it as an explicit feedback system.

### Layer 2: Exposure — what you hold

Your portfolio, decomposed: holdings, sectors, market caps. Nothing exotic — but it matters enormously, because the same crash hits a bank stock and a utility stock very differently.

### Layer 3: Vulnerability — how fragile your portfolio is

This is where the interesting math lives:

- **Downside beta with industry fixed effects**: not "how volatile is this stock," but "how much does it fall when the market falls, controlling for its industry."
- **Vine copula tail dependence**: this is the answer to the "correlations converge to 1" problem. A vine copula models the dependency structure between assets explicitly — including the *tail* dependency that says "when things get bad, they get bad together." This is the piece that replaces the broken normal-distribution assumption.
- **XBRL financial fragility**: I parse SEC filings (XBRL format) and score each company's financial fragility from its actual reported numbers. Leverage, liquidity, debt maturity — the fundamentals that determine whether a company survives a downturn or becomes a forced seller.
- **Sentiment calibration**: because markets are also narratives. NLP on retail-investor comments adjusts model parameters when sentiment gets euphoric (peak risk) or panicked.

### Layer 4: Loss — what you lose

Monte Carlo simulation across 10,000+ crash events, producing:

- Expected Loss
- VaR at 95% and 99%
- CVaR (the average loss *in* the tail — the number that actually matters)
- Maximum drawdown
- An **Exceedance Probability (EP) curve**: the probability of losing more than X, for every X. This is the insurance-industry curve, transplanted to portfolios.
- Sector-level loss attribution: *which* holdings are doing the damage.
- Position-sizing advice from a risk budget: the more volatile the environment, the smaller the position the model tells you to hold.

## What the tool taught me

Building this was a running argument with my own assumptions. The V1 → V8 history is basically a list of lessons learned the hard way:

- **V1**: The core framework. Monte Carlo + historical crashes + downside beta + VaR/CVaR + EP curve. It worked. It was also naive — a single historical crash is not a distribution.
- **V4 (system dynamics)**: The "aha" moment. Adding the leverage feedback loop changed the loss numbers dramatically — because crashes *cascade*, and single-shot simulations can't see that.
- **V5 (vine copula)**: Replacing the correlation assumption. This is the layer that made the tool honest about crisis behavior. Normal-times models said "you're fine." The vine copula said "you're not."
- **V6 (SDE jump-diffusion)**: Modeling the jumps explicitly. Crashes are not just big moves; they're *discontinuous* moves. Different mathematics entirely.
- **V7 (XBRL + sentiment)**: Adding the fundamentals and the narratives. The market is a machine *and* a crowd.
- **V8**: The full Streamlit web app — because a model nobody can run is a paper, not a tool.

## Three things I'd tell my past self

1. **Thin-tail models are not "simplifications"; they're lies.** Use them for convenience, never for crisis planning.
2. **Cascades are the story.** The difference between a bad day and a crash is feedback loops. If your model doesn't have them, it's modeling a different event.
3. **Tail dependency is the whole game.** Diversification works in normal times and fails exactly when you need it. Model the dependency structure directly, don't assume it away.

## What's next

The tool is open-source, fully documented, and runs locally with one command. There's a web UI, example portfolios, and the full V1→V8 development history in the repo.

**GitHub: [github.com/fengyuGbt/crash_simulator](https://github.com/fengyuGbt/crash_simulator)**

I'm now working on AI-driven contract generation and automated risk-analysis agents — tools that *write* the models, then *verify* them with automated tests, so the quality bar isn't a human staring at a chart.

If you're building risk tools, quant models, or AI automation for financial data — I'd love to hear what's biting you right now. The comments are open.

---

*Built with Python, Streamlit, R (yuima), SDE jump-diffusion, vine copulas, system dynamics, XBRL, and a healthy respect for fat tails.*
