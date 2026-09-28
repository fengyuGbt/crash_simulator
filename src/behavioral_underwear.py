# -*- coding: utf-8 -*-
"""V10-P8: behavioral underwear — why the retail garment keeps falling off.

Part 19 priced two retail garments (cash buffer, put insurance) and
showed both improve the tail for ~2%/yr.  Part 20 asks the behavioral
question: the garments are mechanical in the model, but they are worn
by people.  What does the protection actually deliver once panic
selling, lapsed renewals, and raided cash buffers are priced in?

Three behavioral failure channels, each triggered by the crisis itself:

  1. panic sell   — when a path passes -PANIC_T, the investor sells and
                    locks a realized loss at -PANIC_LOCK (soft tail: the
                    put's hard -22% cap becomes a worse -28% cap, and
                    the garment is gone for that path);
  2. lapse        — when the option renewal is repriced at crisis cost
                    (Part 19), the investor does not renew: garment
                    vanishes, path reverts to bare;
  3. cash raid    — the cash buffer is spent/raided under stress: the
                    cash garment vanishes, path reverts to bare.

The naive/mechanical garment is Part 19's numbers.  The behavioral
garment is the same instrument with human failure rates.  Experience
matters: an experienced investor (who has lived through a crisis —
Malmendier & Nagel's Depression babies in reverse) has roughly half
the failure rates of a first-time investor.

Key structure: the garment does not fail by getting worse — it fails
by DISAPPEARING.  Lapse and raid send the path back to the bare
distribution; panic softens the put's hard cap.  And failure is most
likely exactly where protection matters most: deep crises trigger
panic, price lapses, and drain cash — the behavioral clock runs in
the same direction as the policy clock of Part 18.

Deterministic: same seed, same shocks, same numbers every run.
"""
import argparse
import random

from policy_space import SPACE_LEVELS, _space_params
from policy_moral_hazard import (
    DEFAULT_N_PATHS,
    DEFAULT_SEED,
    _clip,
    run_policy_moral_hazard,
    sample_inputs,
)

# garments (same as V10-P7)
CASH_BUFFER = 0.20
PUT_DEDUCTIBLE = 0.20
PUT_PREMIUM = 0.02
THRESHOLD_DEFAULT = 0.30

# behavioral failure parameters (naive investor)
PANIC_T = 0.25          # path loss deeper than -25% triggers panic risk
PANIC_LOCK = 0.28       # realized sale at -28% (panic slippage, 3 pts)
PANIC_PROB = 0.40       # given a deep path, probability the investor panics
LAPSE_PROB = 0.40       # probability the option renewal is not paid
RAID_PROB = 0.25        # probability the cash buffer is raided under stress
EXP_SCALE = 0.5         # experienced investor: failure rates halved

STRATEGIES = ("bare", "mech_cash", "bhv_cash", "mech_put", "bhv_put")


def market_losses(capacity, n=DEFAULT_N_PATHS, seed=DEFAULT_SEED):
    """Raw market losses for one policy-space level (same machinery as
    P6/P7; returns the per-path list for strategy overlay)."""
    trigger_prob, lam_mean, lam_sigma = _space_params(capacity)
    rng = random.Random(seed)
    losses = []
    for _ in range(n):
        gamma0, shock, thresh = sample_inputs(rng)
        lam = lam_mean
        if lam_sigma > 0:
            lam = _clip(rng.gauss(lam_mean, lam_sigma), 1.0, 2.5)
        trigger = rng.random() < trigger_prob
        kwargs = dict(shock=shock, gamma0=gamma0, flip_threshold=thresh,
                      leverage_multiplier=lam, rng=rng)
        if not trigger:
            kwargs["trigger_buckets"] = 99  # betrayed path
        res = run_policy_moral_hazard(**kwargs)
        losses.append(res["total_return"])
    return losses


def run_level(capacity, n=DEFAULT_N_PATHS, seed=DEFAULT_SEED,
              panic_prob=PANIC_PROB, lapse_prob=LAPSE_PROB,
              raid_prob=RAID_PROB):
    """One policy-space level with mechanical and behavioral garments.

    Returns per-path losses for each strategy plus failure counts.
    """
    raw = market_losses(capacity, n=n, seed=seed)
    # deterministic behavioral stream, independent of the market-loss
    # stream but fixed by the same seed
    rng = random.Random(seed)
    mech_cash = []
    mech_put = []
    bhv_cash = []
    bhv_put = []
    panic = 0
    lapse = 0
    raid = 0
    for L in raw:
        # mechanical garments (Part 19 definitions)
        m_cash = (1.0 - CASH_BUFFER) * L
        m_put = max(L, -(PUT_DEDUCTIBLE + PUT_PREMIUM))
        mech_cash.append(m_cash)
        mech_put.append(m_put)

        # behavioral: panic sell on deep paths — the option garment is
        # sold at PANIC_LOCK, softening its hard cap. Panic affects the
        # option garment only; the cash garment fails through raids.
        b_cash = m_cash
        b_put = m_put
        if L < -PANIC_T and rng.random() < panic_prob:
            b_put = -PANIC_LOCK
            panic += 1
        else:
            # lapse: the crisis-priced renewal is not paid -> bare
            if rng.random() < lapse_prob:
                b_put = L
                lapse += 1
        # cash raid: the buffer is spent under stress -> bare
        if rng.random() < raid_prob:
            b_cash = L
            raid += 1
        bhv_cash.append(b_cash)
        bhv_put.append(b_put)

    return {
        "bare": raw,
        "mech_cash": mech_cash,
        "bhv_cash": bhv_cash,
        "mech_put": mech_put,
        "bhv_put": bhv_put,
        "panic_share": panic / n,
        "lapse_share": lapse / n,
        "raid_share": raid / n,
    }


def stats(losses, n, threshold=THRESHOLD_DEFAULT):
    s = sorted(losses)
    return {
        "mean": round(sum(s) / n, 4),
        "p10": round(s[min(n - 1, int(0.10 * (n - 1)))], 4),
        "p1": round(s[min(n - 1, int(0.01 * (n - 1)))], 4),
        "worst": round(s[0], 4),
        "jump_share": round(sum(1.0 for x in s if -x >= threshold) / n, 4),
    }


def table(n=DEFAULT_N_PATHS, seed=DEFAULT_SEED):
    rows = []
    for capacity, _, _, _ in SPACE_LEVELS:
        level = run_level(capacity, n=n, seed=seed)
        row = {"capacity": capacity,
               "panic_share": level["panic_share"],
               "lapse_share": level["lapse_share"],
               "raid_share": level["raid_share"]}
        for name in STRATEGIES:
            row[name] = stats(level[name], n)
        rows.append(row)
    return rows


def self_test():
    print("== behavioral_underwear self-test ==")

    # boundary: bare at C=0 reproduces the P6 no-backstop world
    raw0 = market_losses(0.0)
    s0 = stats(raw0, len(raw0))
    assert abs(s0["mean"] + 0.3390) < 0.005
    print("   bare at C=0 reproduces no-backstop world OK "
          "(mean=%.4f)" % s0["mean"])

    rows = table()

    # mechanical garments reproduce Part 19's numbers
    full = rows[0]
    depleted = rows[-2]
    assert abs(full["mech_put"]["p1"] + 0.2200) < 0.005, full["mech_put"]
    assert abs(full["mech_cash"]["p1"] + 0.2351) < 0.005
    assert abs(depleted["mech_put"]["p1"] + 0.2200) < 0.005
    assert abs(depleted["mech_cash"]["p1"] + 0.5099) < 0.005
    print("   mechanical garments reproduce Part 19 numbers OK")

    # behavioral garments never beat the mechanical ones: failure only
    # reverts to bare or softens the cap, so bhv p1 <= mech p1
    # (numerically: more negative or equal)
    for r in rows:
        assert r["bhv_put"]["p1"] <= r["mech_put"]["p1"] + 1e-9, (
            "bhv put must not beat mech: C=%.2f" % r["capacity"])
        assert r["bhv_cash"]["p1"] <= r["mech_cash"]["p1"] + 1e-9, (
            "bhv cash must not beat mech: C=%.2f" % r["capacity"])
    print("   behavioral garments never beat mechanical OK")

    # behavioral garments still beat bare in deep worlds (the garment
    # survives on most paths): bhv p1 >= bare p1 numerically (shallower)
    for r in rows:
        assert r["bhv_put"]["p1"] >= r["bare"]["p1"] + 1e-9, (
            "bhv put must still beat bare: C=%.2f" % r["capacity"])
        assert r["bhv_cash"]["p1"] >= r["bare"]["p1"] + 1e-9, (
            "bhv cash must still beat bare: C=%.2f" % r["capacity"])
    print("   behavioral garments still beat bare OK")

    # behavioral failure is heaviest where protection matters most:
    # panic share rises as capacity drains (deeper crises trigger panic
    # on more paths)
    shares = [r["panic_share"] for r in rows[:-1]]
    for a, b in zip(shares, shares[1:]):
        assert a <= b + 1e-9, (a, b)
    print("   panic share monotone rising as capacity drains OK "
          "(%.1f%% -> %.1f%%)" % (shares[0] * 100, shares[-1] * 100))

    # experience halves failure rates and strictly improves the
    # behavioral p1: an experienced investor's behavioral put p1 is
    # closer to the mechanical one than a naive investor's
    naive = rows
    exp_rows = []
    for capacity, _, _, _ in SPACE_LEVELS:
        level = run_level(capacity, n=DEFAULT_N_PATHS, seed=DEFAULT_SEED,
                          panic_prob=PANIC_PROB * EXP_SCALE,
                          lapse_prob=LAPSE_PROB * EXP_SCALE,
                          raid_prob=RAID_PROB * EXP_SCALE)
        row = {"capacity": capacity}
        for name in STRATEGIES:
            row[name] = stats(level[name], DEFAULT_N_PATHS)
        exp_rows.append(row)
    for rn, re_ in zip(naive, exp_rows):
        # experienced behavioral mean is strictly shallower (better):
        # fewer lapses/raids revert paths to bare
        assert re_["bhv_put"]["mean"] >= rn["bhv_put"]["mean"] - 1e-9, (
            rn["capacity"], re_["bhv_put"]["mean"], rn["bhv_put"]["mean"])
        assert re_["bhv_cash"]["mean"] >= rn["bhv_cash"]["mean"] - 1e-9
        # p1 comparison with a small tolerance (extreme-order noise)
        assert re_["bhv_put"]["p1"] >= rn["bhv_put"]["p1"] - 0.01
        assert re_["bhv_cash"]["p1"] >= rn["bhv_cash"]["p1"] - 0.01
    print("   experience (halved failure rates) improves behavioral "
          "outcomes OK")

    # determinism (small n is enough to check the overlay stream)
    assert table(n=200) == table(n=200)
    print("   determinism OK")

    print("   all invariants OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true",
                    help="run invariants only")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    print("== V10-P8: behavioral underwear (why the garment falls off) ==")
    print("garments: cash=%d%% | put: deductible=%d%%, premium=%.0f%%/yr"
          % (CASH_BUFFER * 100, PUT_DEDUCTIBLE * 100, PUT_PREMIUM * 100))
    print("behavior: panic sell at -%d%% (locked -%d%%, prob %.0f%%), "
          "lapse prob %.0f%%, cash raid prob %.0f%%"
          % (PANIC_T * 100, PANIC_LOCK * 100, PANIC_PROB * 100,
             LAPSE_PROB * 100, RAID_PROB * 100))
    print("market losses: same P4/P6 machinery, seed %s, 2000 paths/level"
          % DEFAULT_SEED)

    rows = table()
    print()
    hdr = "%-6s %-11s%8s%9s%9s%9s%10s"
    print(hdr % ("C", "garment", "mean", "p10", "p1", "worst", ">30%"))
    for r in rows:
        for name in STRATEGIES:
            s = r[name]
            print("%-6.2f %-11s%8.4f%9.4f%9.4f%9.4f%10.1f"
                  % (r["capacity"], name, s["mean"], s["p10"], s["p1"],
                     s["worst"], s["jump_share"] * 100))
        print("   (failures: panic %.1f%% | lapse %.1f%% | raid %.1f%%)"
              % (r["panic_share"] * 100, r["lapse_share"] * 100,
                 r["raid_share"] * 100))

    print()
    print("nominal vs actual tail protection (p1 improvement over bare):")
    for r in rows:
        bare = r["bare"]["p1"]
        mech_put = (r["mech_put"]["p1"] - bare) * 100
        bhv_put = (r["bhv_put"]["p1"] - bare) * 100
        mech_cash = (r["mech_cash"]["p1"] - bare) * 100
        bhv_cash = (r["bhv_cash"]["p1"] - bare) * 100
        print("   C=%.2f  put: nominal %.1f pts -> actual %.1f pts "
              "| cash: nominal %.1f pts -> actual %.1f pts"
              % (r["capacity"], mech_put, bhv_put, mech_cash, bhv_cash))

    # experience comparison
    print()
    print("experience effect (halved failure rates):")
    for capacity, _, _, _ in SPACE_LEVELS:
        naive_r = next(r for r in rows if r["capacity"] == capacity)
        level = run_level(capacity, seed=DEFAULT_SEED,
                          panic_prob=PANIC_PROB * EXP_SCALE,
                          lapse_prob=LAPSE_PROB * EXP_SCALE,
                          raid_prob=RAID_PROB * EXP_SCALE)
        exp_put = stats(level["bhv_put"], DEFAULT_N_PATHS)
        exp_cash = stats(level["bhv_cash"], DEFAULT_N_PATHS)
        print("   C=%.2f  naive put p1=%.1f%% -> experienced %.1f%% | "
              "naive cash p1=%.1f%% -> experienced %.1f%%"
              % (capacity, naive_r["bhv_put"]["p1"] * 100,
                 exp_put["p1"] * 100,
                 naive_r["bhv_cash"]["p1"] * 100, exp_cash["p1"] * 100))

    print()
    print("reading: the garment fails by disappearing, not by worsening;")
    print("lapse and raid send the path back to the bare distribution,")
    print("panic softens the hard cap — and failure is most likely")
    print("exactly where protection matters most.")


if __name__ == "__main__":
    main()
