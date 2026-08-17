"""Held-out verifier cases not fully specified in instruction.md."""

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
    assert_schedule_invariants(result, now_iso="2026-06-15T12:00:00.123Z")


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
    assert result["audit"]["capped"] is False
    assert_schedule_invariants(result, now_iso="2026-03-01T00:00:00Z")


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
    assert_schedule_invariants(result, now_iso="2026-03-01T00:00:00Z")


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
    assert_schedule_invariants(result, now_iso="2026-03-01T00:00:00Z")


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
    assert_schedule_invariants(result, now_iso="2026-06-15T12:00:00.123Z")


def test_dead_letter_not_one_attempt_late(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_dl001",
        failed_attempt=4,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["status"] == "dead_letter"
    assert result["next_attempt_at"] is None
    assert_schedule_invariants(result, now_iso="2026-03-01T00:00:00Z")


def test_no_retry_after_records_none_in_audit(scheduler, policy):
    result = scheduler.compute_schedule(
        delivery_id="wh_no_ra",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["audit"]["retry_after_applied_ms"] is None


@pytest.mark.parametrize(
    "delivery_id,failed_attempt,now_iso,retry_after_seconds,policy_kwargs",
    [
        ("wh_unseen_7f3a", 1, "2026-04-10T08:30:00Z", None, {}),
        ("wh_unseen_7f3a", 2, "2026-04-10T08:30:00Z", None, {}),
        ("wh_unseen_b901", 1, "2026-07-01T00:00:00.500Z", 3, {}),
        ("wh_unseen_c2d4", 3, "2026-11-20T15:45:12.250Z", None, {"multiplier": 1.5}),
        ("wh_unseen_e8aa", 2, "2026-01-05T00:00:00Z", None, {"jitter_ratio": 0.0}),
    ],
)
def test_unpublished_cases_match_spec_reference(
    scheduler,
    delivery_id,
    failed_attempt,
    now_iso,
    retry_after_seconds,
    policy_kwargs,
):
    """Anti-gaming: held-out IDs and policies verified against sealed spec reference."""
    base = default_policy()
    from webhooks.policy import RetryPolicy

    policy = RetryPolicy(
        max_attempts=policy_kwargs.get("max_attempts", base.max_attempts),
        base_delay_ms=policy_kwargs.get("base_delay_ms", base.base_delay_ms),
        multiplier=policy_kwargs.get("multiplier", base.multiplier),
        max_delay_ms=policy_kwargs.get("max_delay_ms", base.max_delay_ms),
        jitter_ratio=policy_kwargs.get("jitter_ratio", base.jitter_ratio),
    )
    expected = compute_schedule_reference(
        delivery_id=delivery_id,
        failed_attempt=failed_attempt,
        policy=policy,
        now_iso=now_iso,
        retry_after_seconds=retry_after_seconds,
    )
    result = scheduler.compute_schedule(
        delivery_id=delivery_id,
        failed_attempt=failed_attempt,
        policy=policy,
        now_iso=now_iso,
        retry_after_seconds=retry_after_seconds,
    )
    assert result == expected
    assert_schedule_invariants(result, now_iso=now_iso)


def test_max_attempts_one_dead_letters_immediately(scheduler):
    from webhooks.policy import RetryPolicy

    single_shot = RetryPolicy(
        max_attempts=1,
        base_delay_ms=1000,
        multiplier=2.0,
        max_delay_ms=10000,
        jitter_ratio=0.2,
    )
    result = scheduler.compute_schedule(
        delivery_id="wh_single",
        failed_attempt=1,
        policy=single_shot,
        now_iso="2026-03-01T00:00:00Z",
    )
    assert result["status"] == "dead_letter"
    assert result["exhausted"] is True
    assert_schedule_invariants(result, now_iso="2026-03-01T00:00:00Z")


def test_retry_after_does_not_flip_capped_when_raw_under_cap(scheduler, policy):
    """capped reflects pre-Retry-After exponential, not the raised floor."""
    result = scheduler.compute_schedule(
        delivery_id="wh_retry01",
        failed_attempt=1,
        policy=policy,
        now_iso="2026-03-01T00:00:00Z",
        retry_after_seconds=5,
    )
    assert result["audit"]["capped"] is False
    assert result["audit"]["exponential_delay_ms"] == 5000


def test_rejects_invalid_timestamp_format(scheduler, policy):
    with pytest.raises(ValueError, match="timestamp must be UTC with Z suffix"):
        scheduler.compute_schedule(
            delivery_id="wh_bad_ts",
            failed_attempt=1,
            policy=policy,
            now_iso="2026-03-01T00:00:00+00:00",
        )
