"""Visible verifier cases mirrored in instruction.md for agent self-check."""

from __future__ import annotations

import pytest

from helpers import default_policy, load_scheduler


@pytest.fixture(scope="module")
def scheduler():
    return load_scheduler()


@pytest.fixture(scope="module")
def policy():
    return default_policy()


def test_result_shape(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_shape01",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    expected_keys = {
        "next_attempt_at",
        "delay_ms",
        "attempt_number",
        "exhausted",
        "status",
        "audit",
    }
    assert expected_keys.issubset(result.keys())
    assert set(result["audit"].keys()) == {
        "exponential_delay_ms",
        "retry_after_applied_ms",
        "jitter_factor",
        "capped",
    }


def test_first_failure_backoff_and_jitter(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_abc123",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["status"] == "scheduled"
    assert result["exhausted"] is False
    assert result["attempt_number"] == 2
    assert result["delay_ms"] == 916
    assert result["next_attempt_at"] == "2026-03-01T00:00:00.916Z"
    assert result["audit"]["exponential_delay_ms"] == 1000
    assert result["audit"]["jitter_factor"] == "-0.0835"
    assert result["audit"]["capped"] is False
    from invariants import assert_schedule_invariants

    assert_schedule_invariants(result, now_iso="2026-03-01T00:00:00Z")


def test_second_failure_doubles_backoff(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_abc123",
        failed_attempt=2,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["attempt_number"] == 3
    assert result["delay_ms"] == 1684
    assert result["audit"]["exponential_delay_ms"] == 2000
    assert result["audit"]["jitter_factor"] == "-0.1582"


def test_dead_letter_on_final_failure(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_abc123",
        failed_attempt=4,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["exhausted"] is True
    assert result["status"] == "dead_letter"
    assert result["next_attempt_at"] is None
    assert result["attempt_number"] is None
    assert result["delay_ms"] == 0


def test_rejects_non_positive_failed_attempt(scheduler, policy):
    with pytest.raises(ValueError, match="failed_attempt must be >= 1"):
        scheduler.compute_schedule(
            delivery_id="wh_bad",
            failed_attempt=0,
            policy=policy,
            now_iso="2026-03-01T00:00:00Z",
        )
