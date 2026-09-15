"""
generate_transactions.py
Generates 1M+ synthetic financial transactions with injected quality
issues (duplicates, NULLs, invalid timestamps, extreme amounts) and
one deliberate volume/amount anomaly burst (simulating a fraud-style
spike), so downstream detection can be objectively measured.

IMPORTANT: this is 100% synthetic data — no real banking or customer
data is used or required anywhere in this project.
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(99)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

N_TRANSACTIONS = 1_000_000
REGIONS = ["TX", "CA", "NY", "FL", "IL", "WA", "GA", "OH"]
MERCHANTS = [f"Merchant_{i}" for i in range(1, 51)]
CURRENCIES = ["USD"] * 97 + ["EUR", "GBP", "CAD"]  # mostly USD


def generate(n: int = N_TRANSACTIONS) -> pd.DataFrame:
    ids = np.arange(1, n + 1)
    customer_ids = RNG.integers(10_000, 200_000, size=n)
    regions = RNG.choice(REGIONS, size=n)
    merchants = RNG.choice(MERCHANTS, size=n)
    currencies = RNG.choice(CURRENCIES, size=n)
    amounts = np.round(RNG.gamma(shape=2.0, scale=45.0, size=n) + 1, 2)  # right-skewed, realistic
    timestamps = pd.Timestamp("2026-08-01") + pd.to_timedelta(
        RNG.integers(0, 30 * 24 * 60 * 60, size=n), unit="s"
    )

    df = pd.DataFrame(
        {
            "transaction_id": ids,
            "customer_id": customer_ids,
            "amount": amounts,
            "timestamp": timestamps,
            "merchant": merchants,
            "region": regions,
            "currency": currencies,
        }
    )

    # --- Inject a deliberate fraud-style anomaly burst -------------------
    # ~500 transactions in TX, in a narrow 2-hour overnight window,
    # with amounts far above normal — the pattern the detector should catch.
    burst_n = 700
    burst_idx = RNG.choice(df.index, size=burst_n, replace=False)
    # Concentrate the whole burst inside a single hour bucket (02:00-02:59)
    # so it registers as one clear volume+amount spike window.
    burst_time = pd.Timestamp("2026-08-15 02:00:00") + pd.to_timedelta(
        RNG.integers(0, 3599, size=burst_n), unit="s"
    )
    df.loc[burst_idx, "region"] = "TX"
    df.loc[burst_idx, "timestamp"] = burst_time
    df.loc[burst_idx, "amount"] = np.round(RNG.uniform(800, 3000, size=burst_n), 2)

    # --- Inject data quality issues ---------------------------------------
    # Duplicates (~0.5%)
    dup_rows = df.sample(frac=0.005, random_state=1)
    df = pd.concat([df, dup_rows], ignore_index=True)

    # NULLs in amount (~0.3%) and merchant (~0.2%)
    null_amount_idx = df.sample(frac=0.003, random_state=2).index
    df.loc[null_amount_idx, "amount"] = np.nan
    null_merchant_idx = df.sample(frac=0.002, random_state=3).index
    df.loc[null_merchant_idx, "merchant"] = None

    # Invalid timestamps (future dates, ~0.1%)
    invalid_ts_idx = df.sample(frac=0.001, random_state=4).index
    df.loc[invalid_ts_idx, "timestamp"] = pd.Timestamp("2099-01-01")

    # A few extreme/negative amounts unrelated to the fraud burst (~0.05%)
    extreme_idx = df.sample(n=100, random_state=5).index
    df.loc[extreme_idx, "amount"] = RNG.choice([-50, 250000], size=100)

    return df.reset_index(drop=True)


if __name__ == "__main__":
    df = generate()
    out = DATA_DIR / "transactions.parquet"
    df.to_parquet(out, index=False)
    print(f"Generated {len(df):,} synthetic transactions -> {out}")
