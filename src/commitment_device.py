# -*- coding: utf-8 -*-
"""V10-P9: commitment devices — what "better defaults" are worth.

Part 20 priced the behavioral gap: panic, lapse, and raids eat 73-96%
of the garment's nominal protection, and the binding constraint is the
wearer, not the contract.  This part asks the design question: what is
the value of the mechanisms that make the garment stay on?

The answer is parameterized by a commitment strength c in [0,1]:

  c = 0  -> purely discretionary behavior (Part 20's naive investor);
  c = 1  -> fully automatic (the mechanical garment of Part 19, every
            behavioral failure rescued by standing renewal, separate
            accounts, and written rules).

Mechanically, commitment is a RESCUE layer on top of Part 20's
behavioral layer: the same shocks, the same panic impulses, lapses, and
raids occur (P8's numbers are the c=0 baseline), and each failed path
is rescued back to the mechanical outcome with probability c.  Every
path therefore improves monotonically in c by construction, and c=0
reproduces Part 20's published numbers exactly.

Commitment is not free.  Standing renewals, separate accounts, written
rules, and automated execution carry a cost per full unit of
commitment per year (cheap scenario: 0.5%/yr; expensive: 2%/yr).  The
net value of commitment is therefore:

  net p1 = behavioral p1(c) - cost(c)

The interesting questions the numbers answer:
  - is the marginal value of commitment decreasing (the first unit
    carries most of the protection)?
  - where is the optimal commitment strength, and does it move with
    policy capacity C and with the cost of commitment?
  - in the calm world, is any commitment worth its cost at all?

Deterministic: same seed, same shocks, same numbers every run.
"""
import argparse
import random

from policy_space import SPACE_LEVELS
from behavioral_underwear import (
    PANIC_PROB,
    LAPSE_PROB,
    RAID_PROB,
    PANIC_T,
    PANIC_LOCK,
    CASH_BUFFER,
    PUT_DEDUCTIBLE,
    PUT_PREMIUM,
    run_level,
    stats,
)

# commitment grid and cost
COMMIT_LEVELS = (0.00, 0.25, 0.50, 0.75, 1.00)
COMMIT_COST = 0.005          # cheap: 0.5%/yr of cost at full commitment
COMMIT_COST_HIGH = 0.020     # expensive: 2.0%/yr at full commitment
DEFAULT_N = 2000
DEFAULT_SEED = 20260921


def run_commitment(capacity, c, n=DEFAULT_N, seed=DEFAULT_SEED,
                   cost=COMMIT_COST):
    """One capacity level at one commitment strength.

    Baseline is Part 20's behavioral layer (P8, c=0 exact).  Each failed
    path is then rescued back to the mechanical outcome with probability
    c.  Returns per-path losses (bare, mechanical, behavioral gross and
    net of cost) plus failure counts.
    """
    base = run_level(capacity, n=n, seed=seed)
    raw = base["bare"]
    rng = random.Random(seed + 1)  # deterministic rescue stream
    mech_put = []
    mech_cash = []
    bhv_put = []
    bhv_cash = []
    for i, L in enumerate(raw):
        m_put = base["mech_put"][i]
        m_cash = base["mech_cash"][i]
        b_put = base["bhv_put"][i]
        b_cash = base["bhv_cash"][i]
        # rescue: a failed path returns to the mechanical outcome
        # with probability c (monotone in c by construction)
        if b_put != m_put:
            if rng.random() < c:
                b_put = m_put
        if b_cash != m_cash:
            if rng.random() < c:
                b_cash = m_cash
        mech_put.append(m_put)
        mech_cash.append(m_cash)
        bhv_put.append(b_put)
        bhv_cash.append(b_cash)
    cost_val = cost * c
    return {
        "bare": raw,
        "mech_put": mech_put,
        "mech_cash": mech_cash,
        "bhv_put": bhv_put,                # gross of cost (protection value)
        "bhv_cash": bhv_cash,
        "bhv_put_net": [x - cost_val for x in bhv_put],
        "bhv_cash_net": [x - cost_val for x in bhv_cash],
        "panic_share": base["panic_share"],
        "lapse_share": base["lapse_share"],
        "raid_share": base["raid_share"],
    }


def table(n=DEFAULT_N, seed=DEFAULT_SEED):
    """Per capacity level, per commitment level: p1/mean for each view."""
    out = []
    for capacity, _, _, _ in SPACE_LEVELS:
        row = {"capacity": capacity, "levels": {}}
        for c in COMMIT_LEVELS:
            r = run_commitment(capacity, c, n=n, seed=seed)
            row["levels"][c] = {
                "bare": stats(r["bare"], n),
                "mech_put": stats(r["mech_put"], n),
                "mech_cash": stats(r["mech_cash"], n),
                "bhv_put": stats(r["bhv_put"], n),
                "bhv_cash": stats(r["bhv_cash"], n),
                "bhv_put_net": stats(r["bhv_put_net"], n),
                "bhv_cash_net": stats(r["bhv_cash_net"], n),
                "panic_share": r["panic_share"],
                "lapse_share": r["lapse_share"],
                "raid_share": r["raid_share"],
            }
        out.append(row)
    return out


def self_test():
    print("== commitment_device self-test ==")

    # c=0 reproduces Part 20's published naive numbers exactly
    r0 = run_commitment(0.25, 0.00)
    s0 = stats(r0["bhv_put"], DEFAULT_N)
    assert abs(s0["p1"] + 0.6193) < 0.005, s0["p1"]
    r1 = run_commitment(1.00, 0.00)
    s1 = stats(r1["bhv_put"], DEFAULT_N)
    assert abs(s1["p1"] + 0.2847) < 0.005, s1["p1"]
    print("   c=0 reproduces Part 20 published numbers OK")

    # c=1 (without cost) reproduces the mechanical garment
    rc = run_commitment(0.25, 1.00)
    sc = stats(rc["bhv_put"], DEFAULT_N)
    assert abs(sc["p1"] + 0.2200) < 0.005, sc["p1"]
    print("   c=1 (no cost) reproduces Part 19 mechanical numbers OK")

    # gross behavioral p1 is monotone in c (rescue-by-construction,
    # so statistics are monotone without extreme-order noise)
    for capacity, _, _, _ in SPACE_LEVELS:
        prev = None
        for c in COMMIT_LEVELS:
            r = run_commitment(capacity, c)
            p = stats(r["bhv_put"], DEFAULT_N)["p1"]
            if prev is not None:
                assert p >= prev - 1e-9, (capacity, c, prev, p)
            prev = p
    print("   gross behavioral p1 monotone in c OK")

    # marginal value is NOT assumed monotone: it depends on the world
    # (extreme-order pinning in calm worlds vs mass rescue in depleted
    # worlds).  Only structural invariants are asserted here; the shape
    # is a finding.  Total improvement is always positive.
    for capacity, _, _, _ in SPACE_LEVELS:
        ps = [stats(run_commitment(capacity, c)["bhv_put"], DEFAULT_N)["p1"]
              for c in COMMIT_LEVELS]
        assert ps[-1] > ps[0] + 0.005, (capacity, ps[0], ps[-1])
    print("   commitment always improves the tail OK (shape is a finding)")

    # even with EXPENSIVE cost, the depleted world (deep tail) buys full
    # commitment: protection of ~40 pts dwarfs 2%/yr
    dep_nets = [run_commitment(0.25, c, cost=COMMIT_COST_HIGH)
                for c in COMMIT_LEVELS]
    dep1 = stats(dep_nets[-1]["bhv_put_net"], DEFAULT_N)["p1"]
    dep_best = max(stats(r["bhv_put_net"], DEFAULT_N)["p1"]
                   for r in dep_nets)
    assert dep1 >= dep_best - 1e-9, (dep1, dep_best)
    print("   depleted world buys full commitment even at high cost OK")

    # determinism
    assert table(n=200) == table(n=200)
    print("   determinism OK")

    # the finding: value concentrates in the last quarter of commitment
    # (extreme-order pinning) — in every world, the 0.75->1.00 step
    # beats the 0->0.25 step for the put garment
    for capacity, _, _, _ in SPACE_LEVELS:
        ps = [stats(run_commitment(capacity, c)["bhv_put"], DEFAULT_N)["p1"]
              for c in COMMIT_LEVELS]
        first = (ps[1] - ps[0]) * 100
        last = (ps[4] - ps[3]) * 100
        assert last > first + 0.5, (capacity, first, last)
    print("   finding: last quarter of commitment carries the tail OK")

    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P9: commitment devices (what better defaults are worth) ==")
    print("commitment c in [0,1]: c=0 naive (Part 20), c=1 automatic (Part 19)")
    print("rescue layer: each behavioral failure (panic/lapse/raid) is")
    print("rescued back to the mechanical outcome with probability c")
    print("commitment cost: cheap %.2f%%/yr | expensive %.2f%%/yr per unit"
          % (COMMIT_COST * 100, COMMIT_COST_HIGH * 100))
    print("market losses: P4/P6 machinery, seed %s, %d paths/level"
          % (DEFAULT_SEED, DEFAULT_N))

    rows = table()
    print()
    print("gross behavioral p1 per commitment level (protection value):")
    print("C      c    put p1   cash p1   put mean  cash mean  panic%%")
    for row in rows:
        for c in COMMIT_LEVELS:
            lv = row["levels"][c]
            print("%-6.2f %-5.2f %8.4f %8.4f %9.4f %9.4f %7.1f"
                  % (row["capacity"], c,
                     lv["bhv_put"]["p1"], lv["bhv_cash"]["p1"],
                     lv["bhv_put"]["mean"], lv["bhv_cash"]["mean"],
                     lv["panic_share"] * 100))

    print()
    print("marginal value of commitment (gross put p1 improvement, pts):")
    print("C      c:0->.25  .25->.5  .5->.75  .75->1   total")
    for row in rows:
        ps = [row["levels"][c]["bhv_put"]["p1"] for c in COMMIT_LEVELS]
        steps = [(ps[i + 1] - ps[i]) * 100 for i in range(len(ps) - 1)]
        total = (ps[-1] - ps[0]) * 100
        print("%-6.2f %9.1f %8.1f %8.1f %8.1f %8.1f"
              % (row["capacity"], steps[0], steps[1], steps[2], steps[3],
                 total))

    print()
    print("net p1 WITH commitment cost (net = protection - cost):")
    print("C      c*cheap  net put@c*  c*expen  net put@c*  bare p1")
    for row in rows:
        bare = row["levels"][0.00]["bare"]["p1"]
        nets_cheap = [(c, run_commitment(row["capacity"], c,
                                         cost=COMMIT_COST)) for c in
                      COMMIT_LEVELS]
        nets_exp = [(c, run_commitment(row["capacity"], c,
                                       cost=COMMIT_COST_HIGH)) for c in
                    COMMIT_LEVELS]
        best_cheap = max(nets_cheap,
                         key=lambda cc: stats(cc[1]["bhv_put_net"],
                                              DEFAULT_N)["p1"])
        best_exp = max(nets_exp,
                       key=lambda cc: stats(cc[1]["bhv_put_net"],
                                            DEFAULT_N)["p1"])
        print("%-6.2f %8.2f %10.4f %8.2f %10.4f %9.4f"
              % (row["capacity"], best_cheap[0],
                 stats(best_cheap[1]["bhv_put_net"], DEFAULT_N)["p1"],
                 best_exp[0],
                 stats(best_exp[1]["bhv_put_net"], DEFAULT_N)["p1"], bare))

    print()
    print("reading: commitment is all-or-nothing —")
    print("the value concentrates in the LAST quarter of commitment")
    print("(0.75->1.00): as long as any behavioral failure survives,")
    print("the worst 1% stays deep, so the tail only pins once the")
    print("rescue rate is near 1.  Cost is not the constraint: even at"),
    print("2%%/yr the optimal c* is 1.00 everywhere.  And the value of"),
    print("full commitment scales with capacity drain: 6.9 pts net in"),
    print("the calm world vs 39.7 pts in the depleted world — the"),
    print("deeper the tail, the more the wearer should automate.")


if __name__ == "__main__":
    main()
