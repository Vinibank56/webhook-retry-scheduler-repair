# Repair the webhook retry scheduler

You are taking over a webhook delivery microservice at `/app`. After a delivery attempt fails, the service must schedule the next attempt using a declarative retry policy. Finance and SRE audited the module and found systematic under- and over-delay bugs that cause duplicate charges and missed SLA windows.

Your job is to **fix only** `/app/webhooks/scheduler.py`. The companion modules (`policy.py`, `jitter.py`, `time_utils.py`) are correct — do not modify them.

## Background

The scheduler sits on the hot path between your HTTP delivery worker and the outbound queue:

```
Delivery worker                Retry scheduler              Outbound queue
(failed attempt)  ──────────►  compute_schedule()  ─────►  (next_attempt_at, delay_ms)
                                      ▲
                               RetryPolicy + Retry-After header
```

Operations teams rely on its output for three guarantees:

1. **Exhaustion** — stop retrying once the policy limit is reached.
2. **Backoff fairness** — spread retries with exponential delay and deterministic jitter keyed by delivery ID.
3. **Partner compliance** — honor upstream `Retry-After` headers as a minimum delay floor.

The seed implementation passes smoke tests but fails production edge cases. Your fix must satisfy the full contract below, including cases **not** listed in the self-check table.

## Requirements

Implement `compute_schedule` in `/app/webhooks/scheduler.py` that:

- Computes the next retry from `failed_attempt`, `RetryPolicy`, optional `Retry-After`, and `now_iso`.
- Dead-letters when `failed_attempt >= policy.max_attempts`.
- Applies exponential backoff, cap, Retry-After floor, multiplicative jitter, and millisecond timestamp math exactly as specified below.
- Returns the documented dict shape including a complete `audit` block.

## API contract

```python
def compute_schedule(
    *,
    delivery_id: str,
    failed_attempt: int,
    policy: RetryPolicy,
    now_iso: str,
    retry_after_seconds: int | None = None,
) -> dict:
```

All timestamps are UTC ISO-8601 strings ending in `Z`. `failed_attempt` is the attempt number that **just failed** (1 for the first failure, 2 for the second, etc.).

### Return shape

| Field | Type | Meaning |
|-------|------|---------|
| `next_attempt_at` | `str \| None` | When the next attempt should fire, or `None` when exhausted |
| `delay_ms` | `int` | Milliseconds until the next attempt (0 when dead-lettered) |
| `attempt_number` | `int \| None` | The upcoming attempt number, or `None` when dead-lettered |
| `exhausted` | `bool` | Whether no further attempts remain |
| `status` | `str` | `"scheduled"` or `"dead_letter"` |
| `audit` | `dict` | Diagnostic breakdown (see below) |

### Scheduling rules

1. **Dead letter.** If `failed_attempt >= policy.max_attempts`, return immediately with `exhausted=True`, `status="dead_letter"`, `next_attempt_at=None`, `attempt_number=None`, `delay_ms=0`.

2. **Next attempt number.** Otherwise the next attempt is `failed_attempt + 1`.

3. **Exponential backoff (pre-jitter).**
   ```
   raw_exponential = int(policy.base_delay_ms * (policy.multiplier ** (failed_attempt - 1)))
   exponential_delay_ms = min(raw_exponential, policy.max_delay_ms)
   ```

4. **Retry-After floor.** When `retry_after_seconds` is provided:
   ```
   exponential_delay_ms = max(exponential_delay_ms, retry_after_seconds * 1000)
   ```
   Raising the floor does **not** change whether the raw exponential was capped (see audit `capped`).

5. **Deterministic jitter.**
   ```python
   from webhooks.jitter import deterministic_jitter

   jitter_factor, jitter_factor_str = deterministic_jitter(
       delivery_id, next_attempt_number, policy.jitter_ratio
   )
   delay_ms = round(exponential_delay_ms * (1 + jitter_factor))
   ```
   Jitter is **multiplicative**, not additive milliseconds.

6. **Next timestamp.** Use `time_utils.parse_instant`, `add_milliseconds`, and `format_instant`. Do not truncate to whole seconds.

### Audit block

```python
{
    "exponential_delay_ms": int,          # after backoff + Retry-After, before jitter
    "retry_after_applied_ms": int | None, # retry_after_seconds * 1000 if provided else None
    "jitter_factor": str,                 # four-decimal string from deterministic_jitter
    "capped": bool,                       # True iff raw_exponential >= max_delay_ms (before Retry-After)
}
```

### Behavioral invariants (always true)

- When scheduled: `next_attempt_at` equals `now_iso` advanced by exactly `delay_ms` milliseconds.
- Pre-jitter exponential delay **non-decreases** as `failed_attempt` increases (until capped).
- Jitter factor stays within `[-policy.jitter_ratio, +policy.jitter_ratio]`.
- When dead-lettered: `delay_ms == 0` and all nullable fields are `None`.

## Constraints

- Edit **only** `/app/webhooks/scheduler.py`.
- Do not change function signatures or import paths used by the verifier.
- Do not hard-code delivery IDs or expected outputs.
- No runtime network access; all helpers are local.

## Success metrics

You are done when:

1. **Functional** — `compute_schedule` matches the contract for all inputs.
2. **Visible suite** — `pytest /tests/test_visible.py` passes (documented self-check cases).
3. **Hidden suite** — full verifier passes unpublished delivery IDs, policy variants, backoff progression checks, and audit semantics (you cannot inspect these tests, but they grade behavior against the contract).

## How to investigate

1. Read `policy.py`, `jitter.py`, and `time_utils.py` — they implement the primitives correctly.
2. Compare the seed `scheduler.py` against each scheduling rule; several rules are violated independently.
3. Run `pytest /tests/test_visible.py -q` while iterating.

## Self-check examples (visible tests)

**Policy defaults:** `base_delay_ms=1000`, `multiplier=2.0`, `max_delay_ms=10000`, `jitter_ratio=0.2`, `max_attempts=4`.

| Scenario | Inputs | Expected highlights |
|----------|--------|---------------------|
| First failure | `delivery_id="wh_abc123"`, `failed_attempt=1`, `now_iso="2026-03-01T00:00:00Z"` | `attempt_number=2`, `delay_ms=916`, `next_attempt_at="2026-03-01T00:00:00.916Z"` |
| Second failure | same id, `failed_attempt=2` | `attempt_number=3`, `delay_ms=1684` |
| Audit baseline | `failed_attempt=1` | `audit["exponential_delay_ms"] == 1000`, `audit["capped"] is False` |
| Dead letter | `failed_attempt=4` | `exhausted=True`, `status="dead_letter"`, `next_attempt_at is None` |
