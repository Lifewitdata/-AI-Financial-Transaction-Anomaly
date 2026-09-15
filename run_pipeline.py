"""
run_pipeline.py
End-to-end: generate 1M+ synthetic transactions -> run data quality
checks -> run two-layer anomaly detection -> generate an AI/rule-based
investigation summary -> save report + measure throughput.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ingestion.generate_transactions import generate, DATA_DIR
from quality.checks import run_quality_checks
from processing.anomaly import run_anomaly_detection
from ai.explain import explain


def main():
    parquet_path = DATA_DIR / "transactions.parquet"
    if not parquet_path.exists():
        print("Generating synthetic transactions...")
        generate().to_parquet(parquet_path, index=False)

    start = time.time()
    quality = run_quality_checks(parquet_path)
    quality_time = time.time() - start

    df = pd.read_parquet(parquet_path)
    anomaly_start = time.time()
    anomalies = run_anomaly_detection(df)
    anomaly_time = time.time() - anomaly_start

    summary = explain(quality, anomalies)
    total_time = time.time() - start

    report = {
        "quality": quality,
        "anomalies": {
            "point_anomaly_count": anomalies["point_anomaly_count"],
            "pattern_anomaly_windows": anomalies["pattern_anomaly_windows"],
        },
        "ai_summary": summary,
        "performance": {
            "records_processed": quality["total_records"],
            "quality_check_time_sec": round(quality_time, 3),
            "anomaly_detection_time_sec": round(anomaly_time, 3),
            "total_time_sec": round(total_time, 3),
            "throughput_records_per_sec": round(quality["total_records"] / total_time),
        },
    }

    out_path = DATA_DIR / "anomaly_report.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))

    print("=" * 60)
    print(f"Records processed: {report['performance']['records_processed']:,}")
    print(f"Throughput: {report['performance']['throughput_records_per_sec']:,} records/sec")
    print(f"Total time: {report['performance']['total_time_sec']}s")
    print("-" * 60)
    print(f"Duplicates: {quality['duplicate_transaction_ids']} | "
          f"Null amounts: {quality['null_amount_count']} | "
          f"Invalid timestamps: {quality['invalid_future_timestamps']} | "
          f"Negative amounts: {quality['negative_amounts']}")
    print(f"Point anomalies: {anomalies['point_anomaly_count']}")
    print(f"Pattern anomaly windows: {len(anomalies['pattern_anomaly_windows'])}")
    print("-" * 60)
    print(summary)
    print("=" * 60)
    print(f"Full report: {out_path}")


if __name__ == "__main__":
    main()
