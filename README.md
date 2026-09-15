# 💳 AI Financial Transaction Anomaly Pipeline

Processes 1M+ synthetic financial transactions, runs data-quality
validation, and applies two-layer statistical anomaly detection
(point-level outliers + region/time volume-and-amount spike patterns)
to surface a coordinated fraud-style burst — using only aggregated,
non-PII statistics when generating the AI investigation summary.

**No real banking, customer, or financial data is used anywhere in
this project — all data is synthetically generated.**

## Business Problem

Financial systems must process large transaction volumes while
catching duplicate/missing/malformed records and unusual transaction
patterns (e.g. a burst of high-value transactions concentrated in one
region and time window) — the kind of signal that precedes a fraud
investigation.

## Data Source

100% synthetic. `ingestion/generate_transactions.py` generates
1,000,000+ transactions (customer id, amount, timestamp, merchant,
region, currency) with a right-skewed amount distribution, then
injects: duplicate transaction IDs, NULL amounts/merchants, invalid
(future-dated) timestamps, a few extreme/negative amounts, **and** a
deliberate 700-transaction fraud-style burst concentrated in one
region (TX) and one hour window, with amounts 800–3000 vs. a normal
mean around $90 — so detection accuracy can be objectively measured
against a known ground truth.

## Data Dictionary

| Column | Type | Description |
|---|---|---|
| transaction_id | int | Unique transaction identifier |
| customer_id | int | Synthetic customer identifier |
| amount | float | Transaction amount |
| timestamp | datetime | Transaction time |
| merchant | string | One of 50 synthetic merchants |
| region | string | US state code |
| currency | string | Mostly USD, a few EUR/GBP/CAD |

## Architecture

```
Synthetic Transaction Generator (1M+ records)
        ↓
DuckDB Quality Checks (duplicates, nulls, invalid timestamps, negative amounts)
        ↓
Point-Level Anomaly Detection (robust z-score on amount)
        ↓
Pattern-Level Anomaly Detection (region/hour volume + amount spike vs. baseline)
        ↓
AI Investigation Summary (Claude, aggregated stats only — no raw PII sent)
        ↓
Streamlit Dashboard  +  Airflow DAG (10-min schedule, alert on pattern anomaly)
```

## Technology Stack

Python · DuckDB · Pandas/NumPy · PyArrow/Parquet · Apache Airflow (DAG design) · Claude API (optional) · Streamlit · pytest

## Pipeline Flow

1. `ingestion/generate_transactions.py` — generates 1M+ transactions with injected quality issues and a seeded fraud burst
2. `quality/checks.py` — DuckDB checks for duplicates, nulls, invalid timestamps, negative amounts
3. `processing/anomaly.py` — robust z-score point detection + region/hour pattern detection
4. `ai/explain.py` — generates an investigation summary from **aggregated statistics only**
5. `run_pipeline.py` — orchestrates 1–4, measures throughput, writes `data/anomaly_report.json`
6. `dashboard/app.py` — visualizes quality metrics and anomalies
7. `dags/financial_anomaly_dag.py` — reference Airflow scheduling + alerting design

## Data Quality Rules

| Check | Method |
|---|---|
| Duplicates | `COUNT(*) - COUNT(DISTINCT transaction_id)` |
| Nulls | NULL count on `amount`, `merchant` |
| Invalid timestamps | `timestamp > '2026-12-31'` (future-dated) |
| Negative amounts | `amount < 0` |

## AI Component

`ai/explain.py` receives only **aggregated** quality metrics and
anomaly statistics (counts, ratios, region/hour buckets) — never raw
transaction-level records — and asks Claude for a concise
investigation summary and recommended next action. This mirrors how a
real deployment would need to keep PII/PCI-scoped data out of
third-party API calls. Falls back to a deterministic template when no
API key is configured.

## Testing Strategy

`pytest tests/` — 3 tests: (1) quality checks detect all 4 injected
issue types, (2) point-level detection flags only genuinely extreme
values (z-score > 6), (3) pattern-level detection finds the seeded
fraud burst with both volume ratio > 3x and amount ratio > 3x.
**All 3 pass.**

## Performance Results (actually measured)

- **1,005,000 transactions processed** end-to-end (quality checks + both anomaly layers) in **~1.5 seconds**, ≈ **668K–1.2M records/sec** depending on run (see `data/anomaly_report.json` for the exact run).
- **Quality detection**: 5,000 duplicate IDs, 3,014 null amounts, 1,005 invalid timestamps, and dozens of negative/extreme amounts — all correctly identified.
- **Point-level detection**: 2,018 individual transactions flagged as extreme statistical outliers.
- **Pattern-level detection**: correctly identified the single seeded fraud burst — **TX at 2026-08-15 02:00**, 856 transactions (**4.9x** baseline volume), average amount **$1,550 (17.0x** baseline) — with **zero false-positive pattern windows** elsewhere in the dataset.

> These numbers come from this repo's own test run — reproduce with `python run_pipeline.py`.

## Screenshots

_Add a screenshot of `streamlit run dashboard/app.py` here after your first run._

## Limitations

- Anomaly thresholds (z-score > 6, 3x volume/amount ratio) are fixed constants, not learned from historical fraud labels — there is no real fraud ground truth here, only a single seeded synthetic pattern.
- The AI layer never sees raw transaction data by design, which is the right privacy posture but means it can't drill into individual suspicious transactions without a separate, access-controlled path.
- Single seeded anomaly pattern — a real deployment should be tested against multiple, more subtle fraud patterns (slow-drip fraud, account takeover patterns, etc.).

## Future Improvements

- Replace the synthetic generator with a real Kafka producer (reusing the streaming pattern from the mobility project) for true streaming ingestion.
- Add a supervised model trained on labeled fraud data once available, using the current rule-based detectors as engineered features.
- Persist historical baselines instead of recomputing per-run medians, so genuine drift can be distinguished from one-off spikes.

## How to Run

```bash
pip install -r requirements.txt
python run_pipeline.py          # generates 1M+ transactions, runs full pipeline
pytest tests/ -v                # run the test suite (~10s, includes full-scale test)
streamlit run dashboard/app.py  # view the dashboard
```
