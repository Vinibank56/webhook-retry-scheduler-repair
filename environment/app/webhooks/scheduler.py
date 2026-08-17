"""Webhook delivery retry scheduler (broken seed implementation)."""

from __future__ import annotations

from webhooks.jitter import deterministic_jitter
from webhooks.policy import RetryPolicy
from webhooks.time_utils import add_milliseconds, format_instant, parse_instant


def compute_schedule(
    *,
    delivery_id: str,
    failed_attempt: int,
    policy: RetryPolicy,
    now_iso: str,
    retry_after_seconds: int | None = None,
) -> dict:
    """
    Schedule the next webhook delivery attempt after a failure.

    The seed implementation intentionally violates several retry rules.
    """
    if failed_attempt < 1:
        raise ValueError("failed_attempt must be >= 1")

    # BUG: off-by-one — dead-letters one attempt too late
    if failed_attempt > policy.max_attempts:
        return {
            "next_attempt_at": None,
            "delay_ms": 0,
            "attempt_number": None,
            "exhausted": True,
            "status": "dead_letter",
            "audit": {
                "exponential_delay_ms": 0,
                "retry_after_applied_ms": None,
                "jitter_factor": "0.0000",
                "capped": False,
            },
        }

    next_attempt_number = failed_attempt + 1

    # BUG: uses failed_attempt as exponent instead of failed_attempt - 1
    raw_exponential = int(policy.base_delay_ms * (policy.multiplier ** failed_attempt))
    # BUG: never caps at max_delay_ms
    exponential_delay_ms = raw_exponential

    retry_after_applied_ms = None
    # BUG: ignores retry_after_seconds entirely

    jitter_factor, jitter_factor_str = deterministic_jitter(
        delivery_id,
        next_attempt_number,
        policy.jitter_ratio,
    )
    # BUG: treats jitter as additive milliseconds instead of multiplicative factor
    delay_ms = exponential_delay_ms + int(jitter_factor * 1000)

    now = parse_instant(now_iso)
    # BUG: truncates to whole seconds, losing millisecond precision
    next_attempt_at = format_instant(
        add_milliseconds(now, delay_ms).replace(microsecond=0)
    )

    return {
        "next_attempt_at": next_attempt_at,
        "delay_ms": delay_ms,
        "attempt_number": next_attempt_number,
        "exhausted": False,
        "status": "scheduled",
        "audit": {
            "exponential_delay_ms": exponential_delay_ms,
            "retry_after_applied_ms": retry_after_applied_ms,
            "jitter_factor": jitter_factor_str,
            "capped": raw_exponential >= policy.max_delay_ms,
        },
    }
