"""Retry policy definitions for webhook delivery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Declarative retry policy attached to a webhook endpoint."""

    max_attempts: int
    base_delay_ms: int
    multiplier: float
    max_delay_ms: int
    jitter_ratio: float


def default_policy() -> RetryPolicy:
    """Return the standard production retry policy used in verifier fixtures."""
    return RetryPolicy(
        max_attempts=4,
        base_delay_ms=1000,
        multiplier=2.0,
        max_delay_ms=10000,
        jitter_ratio=0.2,
    )
