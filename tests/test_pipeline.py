import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.generate_transactions import generate
from quality.checks import run_quality_checks
from processing.anomaly import detect_point_anomalies, detect_pattern_anomalies


def _small_dataset(tmp_path, n=50_000):
    df = generate(n)
    path = tmp_path / "txns.parquet"
    df.to_parquet(path, index=False)
    return path, df


def test_quality_checks_detect_injected_issues(tmp_path):
    path, df = _small_dataset(tmp_path)
    result = run_quality_checks(path)
    assert result["duplicate_transaction_ids"] > 0
    assert result["null_amount_count"] > 0
    assert result["invalid_future_timestamps"] > 0
    assert result["negative_amounts"] > 0


def test_point_anomaly_detection_flags_extreme_values(tmp_path):
    path, df = _small_dataset(tmp_path)
    flagged = detect_point_anomalies(df)
    assert len(flagged) > 0
    # every flagged transaction should genuinely be far from the median
    assert (flagged["zscore"] > 6.0).all()


def test_pattern_anomaly_detection_finds_seeded_fraud_burst():
    df = generate(1_005_000)  # full size needed for the seeded burst to be statistically visible
    windows = detect_pattern_anomalies(df)
    tx_windows = [w for w in windows if w["region"] == "TX"]
    assert len(tx_windows) >= 1
    burst_window = tx_windows[0]
    assert burst_window["volume_ratio"] > 3.0
    assert burst_window["amount_ratio"] > 3.0
