"""Canonical schedule specification — sealed reference for behavior verification.

This module lives only under tests/ and re-implements the contract from
instruction.md. Hidden tests compare agent output against it for delivery IDs
and parameter combinations never published to the agent.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from webhooks.policy import RetryPolicy


def _deterministic_jitter(delivery_id: str, attempt: int, jitter_ratio: float) -> tuple[float, str]:
    digest = hashlib.sha256(f"{delivery_id}:{attempt}".encode("utf-8")).hexdigest()
    unit = int(digest[:8], 16) / 0xFFFFFFFF
    factor = (unit * 2.0 - 1.0) * jitter_ratio
    return factor, f"{factor:.4f}"


def _parse_instant(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must be UTC with Z suffix")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _format_instant(instant: datetime) -> str:
    utc = instant.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def compute_schedule_reference(
    *,
    delivery_id: str,
    failed_attempt: int,
    policy: RetryPolicy,
    now_iso: str,
    retry_after_seconds: int | None = None,
) -> dict:
    """Reference implementation of the instruction.md contract."""
    if failed_attempt < 1:
        raise ValueError("failed_attempt must be >= 1")

    if failed_attempt >= policy.max_attempts:
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
    raw_exponential = int(policy.base_delay_ms * (policy.multiplier ** (failed_attempt - 1)))
    capped = raw_exponential >= policy.max_delay_ms
    exponential_delay_ms = min(raw_exponential, policy.max_delay_ms)

    retry_after_applied_ms = None
    if retry_after_seconds is not None:
        retry_after_applied_ms = retry_after_seconds * 1000
        exponential_delay_ms = max(exponential_delay_ms, retry_after_applied_ms)

    jitter_factor, jitter_factor_str = _deterministic_jitter(
        delivery_id,
        next_attempt_number,
        policy.jitter_ratio,
    )
    delay_ms = round(exponential_delay_ms * (1 + jitter_factor))

    now = _parse_instant(now_iso)
    next_attempt_at = _format_instant(now + timedelta(milliseconds=delay_ms))

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
            "capped": capped,
        },
    }


def assert_timestamp_consistent(now_iso: str, delay_ms: int, next_attempt_at: str | None) -> None:
    """Behavior invariant: next_attempt_at must equal now + delay_ms."""
    if next_attempt_at is None:
        return
    now = _parse_instant(now_iso)
    expected = _format_instant(now + timedelta(milliseconds=delay_ms))
    assert next_attempt_at == expected
