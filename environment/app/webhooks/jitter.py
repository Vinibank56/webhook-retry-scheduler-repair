"""Deterministic jitter helpers for webhook retry scheduling."""

from __future__ import annotations

import hashlib


def deterministic_jitter(
    delivery_id: str,
    attempt: int,
    jitter_ratio: float,
) -> tuple[float, str]:
    """
    Return a reproducible jitter factor in [-jitter_ratio, +jitter_ratio].

    The factor is derived from SHA-256(delivery_id:attempt) so retries for the
    same delivery are stable across process restarts.
    """
    if jitter_ratio < 0:
        raise ValueError("jitter_ratio must be non-negative")

    digest = hashlib.sha256(f"{delivery_id}:{attempt}".encode("utf-8")).hexdigest()
    unit = int(digest[:8], 16) / 0xFFFFFFFF
    factor = (unit * 2.0 - 1.0) * jitter_ratio
    return factor, f"{factor:.4f}"
