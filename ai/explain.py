"""
explain.py
Turns aggregated (non-sensitive) anomaly statistics into a plain
English investigation summary. Deliberately receives only aggregates
(counts, ratios, region/time buckets) rather than raw transaction-level
records, since sending individual customer-level financial data to a
third-party LLM API would be inappropriate even with synthetic data —
this mirrors how a real deployment would need to handle PII/PCI scope.
"""
import os


def _rule_based(quality: dict, anomalies: dict) -> str:
    lines = []
    lines.append(
        f"Quality: {quality['duplicate_transaction_ids']} duplicate IDs, "
        f"{quality['null_amount_count']} null amounts, "
        f"{quality['invalid_future_timestamps']} invalid timestamps, "
        f"{quality['negative_amounts']} negative amounts detected in "
        f"{quality['total_records']:,} records."
    )
    lines.append(
        f"\nPoint anomalies: {anomalies['point_anomaly_count']} individual "
        f"transactions flagged as extreme outliers (robust z-score > 6)."
    )
    if anomalies["pattern_anomaly_windows"]:
        lines.append(f"\nPattern anomalies: {len(anomalies['pattern_anomaly_windows'])} region/hour window(s) "
                      f"show both a transaction-volume spike and an average-amount spike vs. that region's "
                      f"typical baseline:")
        for w in anomalies["pattern_anomaly_windows"]:
            lines.append(
                f"  - {w['region']} at {w['hour_bucket']}: "
                f"{w['txn_count']} transactions ({w['volume_ratio']:.1f}x baseline volume), "
                f"avg amount ${w['avg_amount']:.2f} ({w['amount_ratio']:.1f}x baseline)."
            )
        lines.append(
            "\nThis combination (volume + amount spike, concentrated in a narrow time "
            "window and single region) is consistent with a coordinated fraud burst "
            "rather than organic demand growth, and should be investigated as such."
        )
    else:
        lines.append("\nNo region/hour windows show a combined volume+amount spike.")
    return "\n".join(lines)


def _llm_based(quality: dict, anomalies: dict) -> str:
    import anthropic

    client = anthropic.Anthropic()
    prompt = f"""You are a fraud/anomaly analyst reviewing aggregated (non-PII)
transaction statistics. Write a concise investigation summary (under 120 words):
what was found, why it's suspicious or not, and one recommended next action.

DATA QUALITY: {quality}
ANOMALIES: {anomalies}
"""
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=350,
                                  messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


def explain(quality: dict, anomalies: dict) -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _llm_based(quality, anomalies)
        except Exception:
            return _rule_based(quality, anomalies)
    return _rule_based(quality, anomalies)
