# Fat Tail Notes — the Crash Simulator series

Building a market stress-testing tool in public, one mechanism at a time.
Each part ships with a real module in `src/` (V9 line: `market_state.py` →
`dealer_gamma.py` → `gamma_flip.py` → `cascade.py` → `mc_mechanism.py`), a
GitHub commit, and this article.

English versions live here (also on [dev.to](https://dev.to/fengyugbt));
Chinese versions in [`zh/`](zh/), also on Zhihu (肥尾笔记).

> AI-assisted writing: every article is written with AI assistance and
> reviewed by the author. English versions carry a freelance CTA; Chinese
> versions carry the AI-assistance disclosure only.

## The series

| Part | Title | Mechanism | Module |
|---|---|---|---|
| 01 | [Building a Crash Simulator](part-01-building-a-crash-simulator.md) | Insurance catastrophe modeling, 4 layers | V1–V8 (`app.py`) |
| 02 | [Vine Copulas](part-02-vine-copulas.md) | Tail dependence when correlations go to 1 | `vine_copula.py` |
| 03 | [The Volatility Skew](part-03-the-volatility-skew.md) | Implied vs realized: why skew stays steep | `market_state.py` |
| 04 | [System Dynamics](part-04-system-dynamics.md) | Leverage → forced selling → more leverage | `system_dynamics.py` |
| 05 | [Short Gamma](part-05-short-gamma.md) | Dealer hedging spiral: -5% → -15.4% (3.07x) | `dealer_gamma.py` (V9-P1) |
| 06 | [Endogenous Hazard](part-06-endogenous-hazard.md) | The hazard layer listens to the market | `hazard.py` (V9-P2) |
| 07 | [Discrete Margin](part-07-discrete-margin.md) | Threshold clustering: 10% skips 12%, lands at 18% | `discrete_margin.py` (V9-P3) |
| 08 | [Mechanism to Distribution](part-08-mechanism-to-distribution.md) | 3.07x is the median of a distribution to -32% | `mc_mechanism.py` (V9-P4) |
| 09 | [The Gamma Flip](part-09-the-gamma-flip.md) | Why the spiral stops: short → long gamma | `gamma_flip.py` (V9-P5) |
| 10 | [The Margin Cascade](part-10-the-margin-cascade.md) | The cascade runs ahead of the flip | `cascade.py` (V9-P6) |
| 11 | [The Twenty-Day Window](part-11-the-twenty-day-window.md) | Price tools vs flow tools; pricing the policy residual | V10-P1 policy layer (planned) |

## Reader feedback drove the roadmap

- Part 1 → Dean Lee (derivatives): endogeneity, dealer short gamma, regime
  instability in copula calibration. → Parts 4–6.
- Part 6 reader: "the aftermath should be a probability distribution." →
  Part 8 + `mc_mechanism.py`.
- Part 6 date bug (Labor Day data stub) → fixed in `market_state.py`
  (`11814bb`), corrected in Part 8.
- Part 10 → Dean Lee: "A VaR that treats the Fed as a residual still prices
  the news shock and misses how long that liquidation window stays open." →
  Part 11 (`backstop = f(trigger, lag, coverage, object)`, V10-P1 planned).

## Layout

```
articles/
  part-XX-*.md          # English
  zh/part-XX-*.md       # Chinese (知乎 肥尾笔记)
src/                    # the modules behind the articles
```

Last synced: 2026-09-17 (parts 1–11).
