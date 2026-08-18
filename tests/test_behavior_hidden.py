"""Hidden behavioral and property tests — verify scheduling logic, not literals alone."""

from __future__ import annotations

import pytest

from helpers import default_policy, load_scheduler
from invariants import assert_schedule_invariants
from spec_reference import compute_schedule_reference


@pytest.fixture(scope="module")
def scheduler():
    return load_scheduler()


@pytest.fixture(scope="module")
def policy():
    return default_policy()


def test_exponential_pre_jitter_doubles_each_failure(scheduler, policy):
    """Verify exponential backoff progression, not just a single timestamp."""
    expected_ms = [1000, 2000, 4000]
    for failed_attempt, expected in enumerate(expected_ms, start=1):
        result = scheduler.compute_schedule(
            delivery_id="wh_backoff_curve",
            failed_attempt=failed_attempt,
            policy=policy,
            now_iso="2026-01-01T00:00:00Z",
        )
        assert result["audit"]["exponential_delay_ms"] == expected
        assert_schedule_invariants(result, now_iso="2026-01-01T00:00:00Z")


def test_jitter_factor_within_policy_bounds(scheduler, policy):
    """Jitter factor must stay inside [-jitter_ratio, +jitter_ratio] for every schedule."""
    for failed_attempt in (1, 2, 3):
        result = scheduler.compute_schedule(
            delivery_id="wh_jitter_bounds",
            failed_attempt=failed_attempt,
            policy=policy,
            now_iso="2026-02-01T00:00:00Z",
        )
        factor = float(result["audit"]["jitter_factor"])
        assert -policy.jitter_ratio <= factor <= policy.jitter_ratio


def test_distinct_delivery_ids_produce_distinct_delays(scheduler, policy):
    """Anti-stub: a hard-coded constant delay cannot pass across delivery IDs."""
    delays = {
        scheduler.compute_schedule(
            delivery_id=delivery_id,
            failed_attempt=1,
            policy=policy,
            now_iso="2026-03-01T00:00:00Z",
        )["delay_ms"]
        for delivery_id in ("wh_dist_a", "wh_dist_b", "wh_dist_c", "wh_dist_d")
    }
    assert len(delays) >= 3


def test_pre_jitter_reaches_cap_under_aggressive_multiplier(scheduler):
    """Stress: large raw exponential must cap before jitter is applied."""
    from webhooks.policy import RetryPolicy

    aggressive = RetryPolicy(
        max_attempts=8,
        base_delay_ms=1000,
        multiplier=2.0,
        max_delay_ms=5000,
        jitter_ratio=0.2,
    )
    result = scheduler.compute_schedule(
        delivery_id="wh_stress_cap",
        failed_attempt=4,
        policy=aggressive,
        now_iso="2026-05-01T00:00:00Z",
    )
    assert result["audit"]["exponential_delay_ms"] == 5000
    assert result["audit"]["capped"] is True
    assert result["delay_ms"] > 0


def test_large_retry_after_overrides_small_exponential(scheduler, policy):
    """Failure scenario: partner mandates long Retry-After on first failure."""
    result = scheduler.compute_schedule(
        delivery_id="wh_partner_slow",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-06-01T00:00:00Z",
        retry_after_seconds=120,
    )
    assert result["audit"]["exponential_delay_ms"] == 120_000
    assert result["delay_ms"] >= 120_000
    assert_schedule_invariants(result, now_iso="2026-06-01T00:00:00Z")


def test_reference_matches_on_randomized_unseen_matrix(scheduler):
    """Property check: agent output equals sealed spec across a behavior matrix."""
    from webhooks.policy import RetryPolicy

    matrix = [
        ("wh_matrix_01", 1, "2026-08-01T12:00:00Z", None, RetryPolicy(4, 500, 2.0, 8000, 0.1)),
        ("wh_matrix_02", 2, "2026-08-02T12:00:00.001Z", 2, RetryPolicy(5, 1000, 2.0, 10000, 0.2)),
        ("wh_matrix_03", 3, "2026-08-03T23:59:59.999Z", None, RetryPolicy(6, 2000, 1.5, 6000, 0.0)),
    ]
    for delivery_id, failed_attempt, now_iso, retry_after, pol in matrix:
        expected = compute_schedule_reference(
            delivery_id=delivery_id,
            failed_attempt=failed_attempt,
            policy=pol,
            now_iso=now_iso,
            retry_after_seconds=retry_after,
        )
        result = scheduler.compute_schedule(
            delivery_id=delivery_id,
            failed_attempt=failed_attempt,
            policy=pol,
            now_iso=now_iso,
            retry_after_seconds=retry_after,
        )
        assert result == expected
        assert_schedule_invariants(result, now_iso=now_iso)


def test_dead_letter_audit_is_zeroed(scheduler, policy):
    """After exhaustion, audit fields must reflect a terminal dead-letter state."""
    result = scheduler.compute_schedule(
        delivery_id="wh_terminal",
        failed_attempt=policy.max_attempts,
        policy=policy,
        now_iso="2026-09-01T00:00:00Z",
    )
    assert result["status"] == "dead_letter"
    assert result["audit"]["exponential_delay_ms"] == 0
    assert result["audit"]["retry_after_applied_ms"] is None
    assert result["audit"]["jitter_factor"] == "0.0000"
    assert result["audit"]["capped"] is False
