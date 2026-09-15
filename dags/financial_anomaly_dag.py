"""
financial_anomaly_dag.py
Reference Airflow DAG. In production, task 1 would consume from a real
Kafka topic (see project 3 for the streaming pattern) rather than
regenerating synthetic data each run.

NOTE: reference implementation, not executed in this sandbox.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    dag_id="ai_financial_anomaly_pipeline",
    default_args={"owner": "data-eng", "retries": 2, "retry_delay": timedelta(minutes=2)},
    schedule_interval=timedelta(minutes=10),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finance", "anomaly-detection", "streaming"],
) as dag:

    def _run(**context):
        import sys
        sys.path.insert(0, "/opt/airflow/dags/repo")
        from run_pipeline import main
        main()

    def _alert_on_pattern_anomaly(**context):
        import json
        report = json.loads(open("/opt/airflow/dags/repo/data/anomaly_report.json").read())
        if report["anomalies"]["pattern_anomaly_windows"]:
            raise ValueError("Pattern-level fraud anomaly detected — see anomaly_report.json")

    run_task = PythonOperator(task_id="run_anomaly_pipeline", python_callable=_run)
    alert_task = PythonOperator(task_id="alert_on_pattern_anomaly", python_callable=_alert_on_pattern_anomaly)
    run_task >> alert_task
