"""
anomaly.py
Two-layer anomaly detection over the transaction stream:

1. Point-level: flag individual transactions whose amount is an
   extreme statistical outlier (z-score vs. the global distribution,
   using a robust median/MAD estimate since amounts are right-skewed).

2. Pattern-level: bucket transactions by (region, hour) and flag
   windows where both transaction volume AND average amount spike far
   above that region's typical hourly baseline — the "$240,000 spike in
   TX at 2am" pattern described in the project brief. This is the
   layer that catches coordinated bursts that no single transaction
   would flag on its own.
"""
import numpy as np
import pandas as pd

POINT_ZSCORE_THRESHOLD = 6.0
VOLUME_SPIKE_MULTIPLIER = 3.0   # flag if hour's volume > 3x region's typical hourly volume
AMOUNT_SPIKE_MULTIPLIER = 3.0   # flag if hour's avg amount > 3x region's typical avg amount


def _robust_zscore(series: pd.Series) -> pd.Series:
    median = series.median()
    mad = (series - median).abs().median() * 1.4826  # normal-consistent MAD
    mad = mad if mad > 0 else 1.0
    return (series - median).abs() / mad


def detect_point_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.dropna(subset=["amount"])
    z = _robust_zscore(clean["amount"])
    flagged = clean[z > POINT_ZSCORE_THRESHOLD].copy()
    flagged["zscore"] = z[z > POINT_ZSCORE_THRESHOLD]
    return flagged[["transaction_id", "region", "amount", "timestamp", "zscore"]]


def detect_pattern_anomalies(df: pd.DataFrame) -> list:
    clean = df.dropna(subset=["amount", "timestamp"]).copy()
    clean["hour_bucket"] = clean["timestamp"].dt.floor("h")

    hourly = (
        clean.groupby(["region", "hour_bucket"])
        .agg(txn_count=("transaction_id", "count"), avg_amount=("amount", "mean"))
        .reset_index()
    )

    baseline = (
        hourly.groupby("region")
        .agg(baseline_count=("txn_count", "median"), baseline_amount=("avg_amount", "median"))
        .reset_index()
    )
    hourly = hourly.merge(baseline, on="region")
    hourly["volume_ratio"] = hourly["txn_count"] / hourly["baseline_count"].replace(0, 1)
    hourly["amount_ratio"] = hourly["avg_amount"] / hourly["baseline_amount"].replace(0, 1)

    flagged = hourly[
        (hourly["volume_ratio"] > VOLUME_SPIKE_MULTIPLIER)
        & (hourly["amount_ratio"] > AMOUNT_SPIKE_MULTIPLIER)
    ].sort_values("hour_bucket")

    return flagged.to_dict("records")


def run_anomaly_detection(df: pd.DataFrame) -> dict:
    point_anomalies = detect_point_anomalies(df)
    pattern_anomalies = detect_pattern_anomalies(df)
    return {
        "point_anomaly_count": len(point_anomalies),
        "point_anomalies_sample": point_anomalies.sort_values("zscore", ascending=False).head(10).to_dict("records"),
        "pattern_anomaly_windows": pattern_anomalies,
    }
