"""Behavior invariants applied to every schedule result."""

from __future__ import annotations

from spec_reference import assert_timestamp_consistent


def assert_schedule_invariants(result: dict, *, now_iso: str) -> None:
    """Check objective-level properties independent of specific test literals."""
    assert isinstance(result, dict)
    assert result["status"] in {"scheduled", "dead_letter"}
    assert isinstance(result["exhausted"], bool)
    assert isinstance(result["delay_ms"], int)
    assert result["delay_ms"] >= 0

    audit = result["audit"]
    assert set(audit.keys()) == {
        "exponential_delay_ms",
        "retry_after_applied_ms",
        "jitter_factor",
        "capped",
    }
    assert isinstance(audit["exponential_delay_ms"], int)
    assert audit["exponential_delay_ms"] >= 0
    assert isinstance(audit["capped"], bool)
    assert isinstance(audit["jitter_factor"], str)

    if result["status"] == "dead_letter":
        assert result["exhausted"] is True
        assert result["next_attempt_at"] is None
        assert result["attempt_number"] is None
        assert result["delay_ms"] == 0
        return

    assert result["exhausted"] is False
    assert result["status"] == "scheduled"
    assert isinstance(result["attempt_number"], int)
    assert result["attempt_number"] >= 2
    assert isinstance(result["next_attempt_at"], str)
    assert result["next_attempt_at"].endswith("Z")
    assert result["delay_ms"] > 0
    assert_timestamp_consistent(now_iso, result["delay_ms"], result["next_attempt_at"])
