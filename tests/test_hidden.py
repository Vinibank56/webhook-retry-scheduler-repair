"""Held-out verifier cases not fully specified in instruction.md."""

from __future__ import annotations

import pytest

from helpers import default_policy, load_scheduler


@pytest.fixture(scope="module")
def scheduler():
    return load_scheduler()


@pytest.fixture(scope="module")
def policy():
    return default_policy()


def test_third_failure_exponential_step(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_abc123",
        failed_attempt=3,
        policy=policy,
        now_iso="2026-06-15T12:00:00.123Z",
    )
    assert result["attempt_number"] == 4
    assert result["delay_ms"] == 4496
    assert result["next_attempt_at"] == "2026-06-15T12:00:04.619Z"
    assert result["audit"]["exponential_delay_ms"] == 4000
    assert result["audit"]["jitter_factor"] == "0.1240"


def test_retry_after_floor_dominates_base_backoff(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_retry01",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
        retry_after_seconds=5,
    )
    assert result["delay_ms"] == 5113
    assert result["audit"]["exponential_delay_ms"] == 5000
    assert result["audit"]["retry_after_applied_ms"] == 5000


def test_max_delay_cap_before_jitter(scheduler):
    from webhooks.policy import RetryPolicy

    tight_cap = RetryPolicy(
        max_attempts=5,
        base_delay_ms=1000,
        multiplier=2.0,
        max_delay_ms=5000,
        jitter_ratio=0.2,
    )
    result = scheduler.compute_schedule(
        delivery_id="wh_cap001",
        failed_attempt=4,
        policy=tight_cap,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["audit"]["exponential_delay_ms"] == 5000
    assert result["audit"]["capped"] is True
    assert result["delay_ms"] == 5960
    assert result["audit"]["jitter_factor"] == "0.1920"


def test_boundary_schedules_last_allowed_attempt(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_bound01",
        failed_attempt=3,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["exhausted"] is False
    assert result["status"] == "scheduled"
    assert result["attempt_number"] == 4


def test_jitter_is_multiplicative_not_additive(scheduler, policy):
    first = scheduler.compute_schedule(
        delivery_id="wh_edge99",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    second = scheduler.compute_schedule(
        delivery_id="wh_edge99",
        failed_attempt=2,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert first["delay_ms"] == 1082
    assert second["delay_ms"] == 2076
    assert first["audit"]["jitter_factor"] == "0.0820"
    assert second["audit"]["jitter_factor"] == "0.0378"


def test_preserves_subsecond_now_timestamp(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_abc123",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-06-15T12:00:00.123Z",
    )
    assert result["next_attempt_at"] == "2026-06-15T12:00:01.039Z"


def test_dead_letter_not_one_attempt_late(scheduler, policy):
    """failed_attempt == max_attempts must dead-letter, not schedule another try."""
    result = scheduler.compute_schedule(
        delivery_id="wh_dl001",
        failed_attempt=4,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["status"] == "dead_letter"
    assert result["next_attempt_at"] is None


def test_no_retry_after_records_none_in_audit(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_no_ra",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["audit"]["retry_after_applied_ms"] is None
