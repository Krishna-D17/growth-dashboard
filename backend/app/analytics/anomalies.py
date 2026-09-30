import math
import statistics
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid

from app.models.profile import ProfileSnapshot
from app.analytics.schemas import AnomalyResult


def calculate_mad(values: List[float], median_val: float) -> float:
    """Calculates Median Absolute Deviation (MAD) for a list of values given their median."""
    abs_deviations = [abs(v - median_val) for v in values]
    return float(statistics.median(abs_deviations))


def detect_follower_anomalies(
    profile_id: uuid.UUID,
    snapshots: List[ProfileSnapshot],
    min_samples: int = 5,
    mad_threshold: float = 3.0
) -> List[AnomalyResult]:
    """
    Detects unusual follower growth spikes or drops using Rolling Median and Median Absolute Deviation (MAD).
    Outputs purely factual observations without causal speculation.
    """
    valid_snapshots = [s for s in snapshots if s.followers is not None]
    if len(valid_snapshots) < min_samples + 1:
        return []

    sorted_snapshots = sorted(valid_snapshots, key=lambda s: s.collected_at)

    # Compute daily growth rate observations
    growth_observations: List[Dict[str, Any]] = []
    for i in range(1, len(sorted_snapshots)):
        prev = sorted_snapshots[i - 1]
        curr = sorted_snapshots[i]

        t_prev = prev.collected_at if prev.collected_at.tzinfo else prev.collected_at.replace(tzinfo=timezone.utc)
        t_curr = curr.collected_at if curr.collected_at.tzinfo else curr.collected_at.replace(tzinfo=timezone.utc)

        elapsed_days = (t_curr - t_prev).total_seconds() / 86400.0
        if elapsed_days <= 0:
            continue

        change = curr.followers - prev.followers
        daily_rate = change / elapsed_days

        growth_observations.append({
            "snapshot": curr,
            "daily_rate": float(daily_rate),
            "observed_at": t_curr
        })

    if len(growth_observations) < min_samples:
        return []

    rates = [obs["daily_rate"] for obs in growth_observations]
    rolling_median = float(statistics.median(rates))
    mad = calculate_mad(rates, rolling_median)

    # If MAD is 0 (e.g. >50% of historical growth values are identical),
    # use Mean Absolute Deviation as effective MAD denominator
    if mad == 0:
        abs_devs = [abs(r - rolling_median) for r in rates]
        mean_abs_dev = statistics.mean(abs_devs)
        mad_effective = mean_abs_dev if mean_abs_dev > 0 else 1.0
    else:
        mad_effective = mad

    anomalies: List[AnomalyResult] = []

    for obs in growth_observations:
        rate = obs["daily_rate"]
        abs_diff = abs(rate - rolling_median)

        score = round(0.6745 * abs_diff / mad_effective, 2)

        if score >= mad_threshold:
            if score >= 8.0:
                severity = "high"
            elif score >= 5.0:
                severity = "medium"
            else:
                severity = "low"

            sign_str = "+" if rate >= 0 else ""
            desc = (
                f"Follower growth of {sign_str}{rate:,.1f}/day is {score} MAD "
                f"from the rolling median baseline of {rolling_median:,.1f}/day."
            )

            anomalies.append(
                AnomalyResult(
                    profile_id=profile_id,
                    metric="follower_growth",
                    baseline={
                        "rolling_median": round(rolling_median, 2),
                        "mad": round(mad, 2),
                        "score": score,
                        "sample_size": len(rates)
                    },
                    observed_value=round(rate, 2),
                    severity=severity,
                    method="rolling_median_mad",
                    description=desc,
                    detected_at=obs["observed_at"]
                )
            )

    return anomalies
