"""
checks.py
DuckDB-backed data quality checks for the transaction stream:
duplicates, nulls, and invalid (future) timestamps.
"""
import duckdb
from pathlib import Path


def run_quality_checks(parquet_path: Path) -> dict:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW txn AS SELECT * FROM read_parquet('{parquet_path}')")

    total = con.execute("SELECT COUNT(*) FROM txn").fetchone()[0]

    dup_count = con.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT transaction_id) FROM txn"
    ).fetchone()[0]

    null_amount = con.execute("SELECT COUNT(*) FROM txn WHERE amount IS NULL").fetchone()[0]
    null_merchant = con.execute("SELECT COUNT(*) FROM txn WHERE merchant IS NULL").fetchone()[0]

    invalid_ts = con.execute(
        "SELECT COUNT(*) FROM txn WHERE timestamp > TIMESTAMP '2026-12-31'"
    ).fetchone()[0]

    negative_amount = con.execute("SELECT COUNT(*) FROM txn WHERE amount < 0").fetchone()[0]

    con.close()

    return {
        "total_records": total,
        "duplicate_transaction_ids": int(dup_count),
        "null_amount_count": int(null_amount),
        "null_merchant_count": int(null_merchant),
        "invalid_future_timestamps": int(invalid_ts),
        "negative_amounts": int(negative_amount),
    }
