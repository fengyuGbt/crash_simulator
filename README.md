# Crash Simulator

## Open to freelance work

I build **AI data automation, Python pipelines, and quantitative risk tools** for hire.
Portfolio: this repo · [ai-agent-demo](https://github.com/fengyuGbt/ai-agent-demo)
Contact: **gopipibank@gmail.com**

---

**Market stress-testing tool for equity portfolios, built on insurance catastrophe-modeling methodology.**

Simulate historical crash scenarios against your portfolio and get quantified answers: *how much could I lose, how bad is the tail, which sectors hurt me most, and how much should I be holding right now?*

---

## Why this tool exists

Most risk tools assume returns follow a normal distribution. Markets don't. In a crisis, correlations converge to 1 and everything falls together — the exact moment standard VaR models fail.

Crash Simulator adapts the **four-layer catastrophe model** (the same framework insurance companies use to price hurricanes and earthquakes) to financial market crashes:

```
  HAZARD        EXPOSURE       VULNERABILITY        LOSS
  (how crashes  (what you      (how fragile         (what you
   happen)       hold)          your portfolio is)   lose)
```

- **Hazard** — how crashes are generated: 6 historical crash events (2008 Financial Crisis, 2020 COVID, 2022 China ADRs, ...), SDE jump-diffusion extreme-event modeling, and a system-dynamics feedback loop (margin calls → forced selling → more margin calls).
- **Exposure** — your portfolio: holdings, industry and market-cap breakdown.
- **Vulnerability** — how fragile your portfolio is: downside beta with industry fixed effects, **Vine copula tail dependency** (crisis correlation modeling — the piece that replaces the broken normal-distribution assumption), XBRL-based financial fragility scoring from SEC filings, and NLP sentiment calibration.
- **Loss** — what you lose: Monte Carlo simulation (10,000+ paths), Expected Loss, VaR 95%/99%, CVaR, max drawdown, loss **Exceedance Probability (EP) curve**, sector loss attribution, and risk-budget position-sizing advice.

## Features

| Layer | Feature |
|---|---|
| Hazard | 6 historical crash scenarios; SDE jump-diffusion (yuima/R parameter estimation); systemic-dynamics leverage feedback loop |
| Vulnerability | Downside beta + industry fixed effects; Vine copula tail dependence; XBRL financial fragility scoring (SEC data); NLP sentiment calibration |
| Loss | Monte Carlo (10,000+ events); EL / VaR 95% / VaR 99% / CVaR / max drawdown; EP curve; sector contribution; position-sizing advice |
| Product | Streamlit web UI; example portfolio or manual stock entry; CSV/TXT report export |

## Quick start

```bash
cd crash_simulator
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

Workflow: load an example portfolio → pick a crash scenario (2008, 2020, 2022, ...) → run the stress test → read the loss distribution, VaR/CVaR, EP curve, sector contribution, and position advice.

## Repository layout

```
crash_simulator/
├── app.py                  # Streamlit web app (~1,500 lines)
├── src/
│   ├── hazard.py           # Historical crash events, SDE event generation
│   ├── jump_diffusion.py   # SDE jump-diffusion extreme-event model
│   ├── system_dynamics.py  # Leverage feedback loop (margin-call spiral)
│   ├── exposure.py         # Portfolio data structures
│   ├── vulnerability.py    # Downside beta + industry fixed effects
│   ├── vine_copula.py      # Vine copula tail dependency
│   ├── xbrl_vulnerability.py  # XBRL financial fragility scoring
│   ├── sentiment_calibration.py # NLP sentiment calibration
│   ├── loss.py             # Monte Carlo, VaR/CVaR, EP curve
│   ├── advice.py           # Risk-budget position sizing
│   └── yuima_integration.py    # R yuima SDE parameter estimation
├── historical_crashes.csv  # 6 historical crash datasets
├── test_v2.py ... test_v5.py  # Versioned test suites
└── install.sh / start_streamlit.sh / git_commit_*.sh  # Ops & release scripts
```

## Development history (V1 → V8)

The project evolved through 8 versioned milestones, each with its own commit history and tests:

| Version | What was added |
|---|---|
| V1 | Core framework: Monte Carlo + 6 historical crashes + downside beta + VaR/CVaR + EP curve |
| V2 | More scenarios, finer industry effects |
| V3 | Parameter tuning, better result output |
| V4 | System dynamics: leverage feedback loop |
| V5 | Vine copula: tail dependency |
| V6 | SDE jump diffusion: extreme-event modeling (yuima integration) |
| V7 | Sentiment calibration + XBRL financial fragility |
| V8 | Full integration into a complete Streamlit web app |

## Use cases

- **Individual investors** — see quantified downside before a drawdown, not after.
- **Small asset managers / family offices** — scenario-based stress testing and risk reporting.
- **Risk education** — a concrete, runnable example of how insurance-catastrophe methods map onto financial risk.

## License

MIT
