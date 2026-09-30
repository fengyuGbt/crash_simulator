# -*- coding: utf-8 -*-
"""V10-P10: the self-exemption loophole — what "this time is different" costs.

Part 21 showed commitment is all-or-nothing: full commitment pins the
worst 1% at the mechanical cap, and the value concentrates in the last
quarter.  This part attacks the device from the other side: the wearer
who exempts himself.  "This time is different."  "I can sell just this
once."  "I'll renew tomorrow."

The new parameter is the exemption rate e in [0,1]: the probability
that, at the moment of crisis, the investor overrides the standing
automatic rule — lets the panic trade through, lets the renewal lapse,
lets the cash raid happen — despite full commitment (c=1).

  e = 0  -> full commitment holds (Part 19's mechanical garment);
  e = 1  -> every impulse overrides the rules (Part 20's naive investor).

Between the extremes, exemption is a HOLE in the rescue layer: under
full commitment, each behavioral failure would be rescued back to the
mechanical outcome with probability 1, and exemption flips a share e of
those rescues back into failures.  Equivalently, the effective rescue
rate is 1 - e, and e=0.25 behaves like commitment strength c=0.75.

The questions the numbers answer:
  - is the damage of exemption linear?  (Part 21 said commitment is
    all-or-nothing; the mirror question is whether a 10% exemption
    rate already destroys most of the garment)
  - how asymmetric is the device: to win you need 100% commitment, to
    lose you need only one override — quantify the asymmetry;
  - does exemption damage scale with capacity drain (is the loophole
    most dangerous exactly when the backstop is least credible)?

Deterministic: same seed, same shocks, same numbers every run.
"""
import argparse
import random

from policy_space import SPACE_LEVELS
from behavioral_underwear import (
    PANIC_PROB,
    LAPSE_PROB,
    RAID_PROB,
    run_level,
    stats,
)

# exemption grid (10% is the dangerous point to test)
EXEMPT_LEVELS = (0.00, 0.10, 0.25, 0.50, 1.00)
DEFAULT_N = 2000
DEFAULT_SEED = 20260921


def run_exemption(capacity, e, n=DEFAULT_N, seed=DEFAULT_SEED):
    """One capacity level at one exemption rate, under full commitment.

    Baseline is Part 20's behavioral layer (P8).  Full commitment (Part
    21, c=1) rescues every behavioral failure back to the mechanical
    outcome; exemption flips a share e of those rescues back into
    failures.  e=0 reproduces Part 19's mechanical numbers, e=1
    reproduces Part 20's naive numbers.
    """
    base = run_level(capacity, n=n, seed=seed)
    raw = base["bare"]
    rng = random.Random(seed + 2)  # deterministic exemption stream
    rescue_p = 1.0 - e
    mech_put = []
    mech_cash = []
    bhv_put = []
    bhv_cash = []
    for i, L in enumerate(raw):
        m_put = base["mech_put"][i]
        m_cash = base["mech_cash"][i]
        b_put = base["bhv_put"][i]
        b_cash = base["bhv_cash"][i]
        if b_put != m_put:
            if rng.random() < rescue_p:
                b_put = m_put
        if b_cash != m_cash:
            if rng.random() < rescue_p:
                b_cash = m_cash
        mech_put.append(m_put)
        mech_cash.append(m_cash)
        bhv_put.append(b_put)
        bhv_cash.append(b_cash)
    return {
        "bare": raw,
        "mech_put": mech_put,
        "mech_cash": mech_cash,
        "bhv_put": bhv_put,
        "bhv_cash": bhv_cash,
        "panic_share": base["panic_share"],
        "lapse_share": base["lapse_share"],
        "raid_share": base["raid_share"],
    }


def table(n=DEFAULT_N, seed=DEFAULT_SEED):
    """Per capacity level, per exemption level: p1/mean for each view."""
    out = []
    for capacity, _, _, _ in SPACE_LEVELS:
        row = {"capacity": capacity, "levels": {}}
        for e in EXEMPT_LEVELS:
            r = run_exemption(capacity, e, n=n, seed=seed)
            row["levels"][e] = {
                "bare": stats(r["bare"], n),
                "mech_put": stats(r["mech_put"], n),
                "bhv_put": stats(r["bhv_put"], n),
                "bhv_cash": stats(r["bhv_cash"], n),
                "panic_share": r["panic_share"],
                "lapse_share": r["lapse_share"],
                "raid_share": r["raid_share"],
            }
        out.append(row)
    return out


def self_test():
    print("== self_exemption self-test ==")

    # e=0 reproduces Part 19's mechanical garment
    r0 = run_exemption(0.25, 0.00)
    s0 = stats(r0["bhv_put"], DEFAULT_N)
    assert abs(s0["p1"] + 0.2200) < 0.005, s0["p1"]
    print("   e=0 reproduces Part 19 mechanical numbers OK")

    # e=1 reproduces Part 20's naive numbers exactly
    r1 = run_exemption(0.25, 1.00)
    s1 = stats(r1["bhv_put"], DEFAULT_N)
    assert abs(s1["p1"] + 0.6193) < 0.005, s1["p1"]
    r1b = run_exemption(1.00, 1.00)
    s1b = stats(r1b["bhv_put"], DEFAULT_N)
    assert abs(s1b["p1"] + 0.2847) < 0.005, s1b["p1"]
    print("   e=1 reproduces Part 20 naive numbers OK")

    # p1 is monotone in e (rescues shrink with e by construction)
    for capacity, _, _, _ in SPACE_LEVELS:
        prev = None
        for e in EXEMPT_LEVELS:
            r = run_exemption(capacity, e)
            p = stats(r["bhv_put"], DEFAULT_N)["p1"]
            if prev is not None:
                assert p <= prev + 1e-9, (capacity, e, prev, p)
            prev = p
    print("   p1 monotone in exemption rate OK")

    # THE FINDING: exemption damage is nonlinear — a 10% exemption rate
    # already destroys most of the commitment's protection in the
    # depleted world.  Quantify: in the depleted world, p1(e=0.10) is
    # closer to p1(e=1.00) than to p1(e=0.00) (the tail stays deep as
    # long as any override can fire).
    dep = next(row for row in table() if row["capacity"] == 0.25)
    p0 = dep["levels"][0.00]["bhv_put"]["p1"]
    p10 = dep["levels"][0.10]["bhv_put"]["p1"]
    p100 = dep["levels"][1.00]["bhv_put"]["p1"]
    d10 = abs(p10 - p100)
    d0 = abs(p10 - p0)
    assert d10 < d0 - 0.01, (p0, p10, p100, d0, d10)
    print("   finding: 10%% exemption already dominates the tail in the "
          "depleted world OK (p1: e=0 %.4f / e=.10 %.4f / e=1 %.4f)"
          % (p0, p10, p100))

    # determinism
    assert table(n=200) == table(n=200)
    print("   determinism OK")

    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P10: the self-exemption loophole ==")
    print("full commitment (c=1) rescues every behavioral failure;")
    print("exemption e flips a share of those rescues back into failures")
    print("market losses: P4/P6 machinery, seed %s, %d paths/level"
          % (DEFAULT_SEED, DEFAULT_N))

    rows = table()
    print()
    print("put p1 per exemption level (worst 1%% loss):")
    print("C      e=0     e=.10   e=.25   e=.50   e=1.00   bare")
    for row in rows:
        lv = row["levels"]
        bare = lv[0.00]["bare"]["p1"]
        print("%-6.2f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f"
              % (row["capacity"],
                 lv[0.00]["bhv_put"]["p1"], lv[0.10]["bhv_put"]["p1"],
                 lv[0.25]["bhv_put"]["p1"], lv[0.50]["bhv_put"]["p1"],
                 lv[1.00]["bhv_put"]["p1"], bare))

    print()
    print("cash p1 per exemption level:")
    print("C      e=0     e=.10   e=.25   e=.50   e=1.00   bare")
    for row in rows:
        lv = row["levels"]
        bare = lv[0.00]["bare"]["p1"]
        print("%-6.2f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f"
              % (row["capacity"],
                 lv[0.00]["bhv_cash"]["p1"], lv[0.10]["bhv_cash"]["p1"],
                 lv[0.25]["bhv_cash"]["p1"], lv[0.50]["bhv_cash"]["p1"],
                 lv[1.00]["bhv_cash"]["p1"], bare))

    print()
    print("damage of exemption (pts of p1 eaten vs e=0, put):")
    print("C      e=.10   e=.25   e=.50   e=1.00   total protection")
    for row in rows:
        lv = row["levels"]
        p0 = lv[0.00]["bhv_put"]["p1"]
        tot = (lv[1.00]["bhv_put"]["p1"] - p0) * 100
        d10 = (lv[0.10]["bhv_put"]["p1"] - p0) * 100
        d25 = (lv[0.25]["bhv_put"]["p1"] - p0) * 100
        d50 = (lv[0.50]["bhv_put"]["p1"] - p0) * 100
        d100 = (lv[1.00]["bhv_put"]["p1"] - p0) * 100
        print("%-6.2f %8.1f %8.1f %8.1f %8.1f %15.1f"
              % (row["capacity"], d10, d25, d50, d100, tot))

    print()
    print("exemption share of protection destroyed (%% of total):")
    print("C      e=.10   e=.25   e=.50   e=1.00")
    for row in rows:
        lv = row["levels"]
        p0 = lv[0.00]["bhv_put"]["p1"]
        tot = (lv[1.00]["bhv_put"]["p1"] - p0) * 100
        if abs(tot) < 1e-9:
            tot = 1e-9
        pct10 = (lv[0.10]["bhv_put"]["p1"] - p0) * 100 / tot * 100
        pct25 = (lv[0.25]["bhv_put"]["p1"] - p0) * 100 / tot * 100
        pct50 = (lv[0.50]["bhv_put"]["p1"] - p0) * 100 / tot * 100
        pct100 = 100.0
        print("%-6.2f %7.1f%% %7.1f%% %7.1f%% %7.1f%%"
              % (row["capacity"], pct10, pct25, pct50, pct100))

    print()
    print("reading: the loophole is asymmetric with the commitment —")
    print("to win you need 100%% commitment (Part 21); to lose you need")
    print("only ONE override.  In the depleted world a 10%% exemption")
    print("rate already eats most of the garment's protection, because")
    print("as long as any override can fire, the worst 1%% stays deep.")
    print("The exemption hole scales with capacity drain: the less"),
    print("credible the backstop, the more dangerous the self-loophole.")


if __name__ == "__main__":
    main()
