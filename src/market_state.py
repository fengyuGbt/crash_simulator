"""Market state indicators from free public data (Cboe VIX/SKEW).

V9-P0: regime-aware hazard inputs -- response to Dean Lee's feedback on
regime instability in copula calibration and endogenous hazard.

Data sources (free, no API key):
  - Cboe VIX history  : https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv
  - Cboe SKEW history : https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv

Usage:
    python3 market_state.py                 # print current regime snapshot
    python3 market_state.py --self-test     # download + validate pipeline

The computed hazard_multiplier can be used by hazard.py to make event
intensity state-dependent (the "endogenous hazard" direction).
"""

import argparse
import datetime as dt
import io
import os
import sys

import pandas as pd
import requests

CBOE_VIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
CBOE_SKEW_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv"
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Regime -> hazard intensity multiplier (used by hazard.py, V9-P2 hook).
REGIME_MULTIPLIER = {"calm": 1.0, "stressed": 1.5, "panic": 2.5}


def _fetch_csv(url, cache_path, timeout=25, use_cache=True):
    """Download a Cboe daily CSV, caching to disk on first success."""
    if use_cache and os.path.exists(cache_path):
        df = pd.read_csv(cache_path)
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        return df
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = [str(c).strip().upper() for c in df.columns]
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df = df.dropna(subset=["DATE"]).sort_values("DATE").reset_index(drop=True)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df.to_csv(cache_path, index=False)
    return df


def load_vix(cache_dir=DEFAULT_CACHE_DIR, use_cache=True):
    """VIX history DataFrame (DATE, OPEN, HIGH, LOW, CLOSE)."""
    return _fetch_csv(CBOE_VIX_URL, os.path.join(cache_dir, "vix_history.csv"), use_cache=use_cache)


def load_skew(cache_dir=DEFAULT_CACHE_DIR, use_cache=True):
    """SKEW history DataFrame (DATE, CLOSE). Cboe serves it as (DATE, SKEW)."""
    df = _fetch_csv(CBOE_SKEW_URL, os.path.join(cache_dir, "skew_history.csv"), use_cache=use_cache)
    if "SKEW" in df.columns and "CLOSE" not in df.columns:
        df = df.rename(columns={"SKEW": "CLOSE"})
    return df


def percentile_rank(series, value):
    """Historical percentile of value within series (0..1), NaN-safe."""
    valid = series.dropna()
    if len(valid) == 0:
        return float("nan")
    return float((valid < value).mean())


def pct_change(series, n):
    """Return latest n-period % change, NaN-safe."""
    valid = series.dropna()
    if len(valid) < n + 1:
        return float("nan")
    base, latest = valid.iloc[-n - 1], valid.iloc[-1]
    if base == 0 or pd.isna(base) or pd.isna(latest):
        return float("nan")
    return float(latest / base - 1.0)


def classify_regime(vix_pctile, skew_pctile, vix_chg_5d, vix_close):
    """Rule-based regime classification (calm / stressed / panic)."""
    if pd.isna(vix_pctile):
        vix_pctile = 0.5
    if pd.isna(skew_pctile):
        skew_pctile = 0.5
    if pd.isna(vix_chg_5d):
        vix_chg_5d = 0.0
    if pd.isna(vix_close):
        vix_close = 20.0
    if vix_pctile >= 0.95 or vix_close >= 40.0:
        return "panic"
    if vix_pctile >= 0.80 or skew_pctile >= 0.90 or vix_chg_5d > 0.15:
        return "stressed"
    return "calm"


def compute_state(vix=None, skew=None, lookback=252 * 5):
    """Build a regime snapshot from VIX/SKEW levels and percentiles.

    Returns a dict with current levels, percentiles, changes, regime and
    the hazard multiplier to feed hazard.py.
    """
    vix = vix if vix is not None else load_vix()
    skew = skew if skew is not None else load_skew()

    close_col = "CLOSE" if "CLOSE" in vix.columns else vix.columns[-1]
    vix_close = float(vix[close_col].iloc[-1])
    skew_close = float(skew[close_col].iloc[-1]) if len(skew) else float("nan")

    recent_vix = vix[close_col].tail(lookback)
    recent_skew = skew[close_col].tail(lookback)

    vix_pctile = percentile_rank(recent_vix, vix_close)
    skew_pctile = percentile_rank(recent_skew, skew_close)
    vix_chg_5d = pct_change(vix[close_col], 5)
    vix_chg_21d = pct_change(vix[close_col], 21)

    regime = classify_regime(vix_pctile, skew_pctile, vix_chg_5d, vix_close)

    return {
        "as_of": str(vix["DATE"].iloc[-1].date()),
        "vix_close": round(vix_close, 2),
        "vix_pctile_5y": round(vix_pctile, 3),
        "vix_chg_5d": round(vix_chg_5d, 4),
        "vix_chg_21d": round(vix_chg_21d, 4),
        "skew_close": round(skew_close, 2) if not pd.isna(skew_close) else None,
        "skew_pctile_5y": round(skew_pctile, 3) if not pd.isna(skew_pctile) else None,
        "regime": regime,
        "hazard_multiplier": REGIME_MULTIPLIER[regime],
    }


def self_test():
    """Download both indices, validate rows/columns, print snapshot."""
    print("== market_state self-test ==")
    vix = load_vix(use_cache=False)
    skew = load_skew(use_cache=False)
    assert len(vix) > 100, f"VIX rows too few: {len(vix)}"
    assert len(skew) > 100, f"SKEW rows too few: {len(skew)}"
    assert {"DATE", "CLOSE"}.issubset(set(vix.columns)), f"VIX cols: {list(vix.columns)}"
    assert {"DATE", "CLOSE"}.issubset(set(skew.columns)), f"SKEW cols: {list(skew.columns)}"
    print(f"  VIX rows: {len(vix)}  ({vix['DATE'].iloc[0].date()} -> {vix['DATE'].iloc[-1].date()})")
    print(f"  SKEW rows: {len(skew)}  ({skew['DATE'].iloc[0].date()} -> {skew['DATE'].iloc[-1].date()})")
    state = compute_state(vix, skew)
    print_state(state)
    print("== self-test OK ==")
    return 0


def print_state(state):
    print("== market state snapshot ==")
    for k, v in state.items():
        print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="Cboe VIX/SKEW market state")
    parser.add_argument("--self-test", action="store_true", help="download + validate pipeline")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    state = compute_state()
    print_state(state)
    return 0


if __name__ == "__main__":
    sys_exit = main()
    sys.exit(sys_exit)
