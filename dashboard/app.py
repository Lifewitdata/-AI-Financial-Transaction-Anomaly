"""
app.py
Streamlit dashboard for the financial transaction anomaly pipeline.
Run with: streamlit run dashboard/app.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT_PATH = ROOT / "data" / "anomaly_report.json"

st.set_page_config(page_title="Financial Anomaly Pipeline", layout="wide")
st.title("💳 AI Financial Transaction Anomaly Pipeline")

if not REPORT_PATH.exists():
    st.warning("No report found. Run `python run_pipeline.py` first.")
    st.stop()

report = json.loads(REPORT_PATH.read_text())
perf = report["performance"]
quality = report["quality"]
anomalies = report["anomalies"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Records processed", f"{perf['records_processed']:,}")
c2.metric("Throughput", f"{perf['throughput_records_per_sec']:,}/sec")
c3.metric("Point anomalies", anomalies["point_anomaly_count"])
c4.metric("Pattern anomaly windows", len(anomalies["pattern_anomaly_windows"]))

st.subheader("Data Quality")
st.dataframe(pd.DataFrame([quality]), use_container_width=True)

st.subheader("Pattern Anomalies (Volume + Amount Spikes)")
if anomalies["pattern_anomaly_windows"]:
    st.dataframe(pd.DataFrame(anomalies["pattern_anomaly_windows"]), use_container_width=True)
else:
    st.success("No combined volume+amount spike windows detected.")

st.subheader("AI Investigation Summary")
st.code(report["ai_summary"], language=None)
st.caption(f"Total pipeline time: {perf['total_time_sec']}s")
