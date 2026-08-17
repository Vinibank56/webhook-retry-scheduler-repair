# Repair the webhook retry scheduler

You are taking over a webhook delivery microservice at `/app`. After a delivery attempt fails, the service must schedule the next attempt using a declarative retry policy. Finance and SRE audited the module and found systematic under- and over-delay bugs that cause duplicate charges and missed SLA windows.

Your job is to **fix only** `/app/webhooks/scheduler.py`. The companion modules (`policy.py`, `jitter.py`, `time_utils.py`) are correct — do not modify them.

## API contract

Implement `compute_schedule` in `/app/webhooks/scheduler.py`:

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

Always return a dict containing at least:

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

3. **Exponential backoff (pre-jitter).** Compute:
   ```
   exponential_delay_ms = min(
       int(policy.base_delay_ms * (policy.multiplier ** (failed_attempt - 1))),
       policy.max_delay_ms,
   )
   ```
   The exponent uses `failed_attempt - 1`, so the first failure (`failed_attempt == 1`) waits one base interval.

4. **Retry-After floor.** When `retry_after_seconds` is provided, raise the delay before jitter:
   ```
   exponential_delay_ms = max(exponential_delay_ms, retry_after_seconds * 1000)
   ```

5. **Deterministic jitter.** Call the provided helper:
   ```python
   from webhooks.jitter import deterministic_jitter

   jitter_factor, jitter_factor_str = deterministic_jitter(
       delivery_id, next_attempt_number, policy.jitter_ratio
   )
   delay_ms = round(exponential_delay_ms * (1 + jitter_factor))
   ```
   Jitter is **multiplicative**, not additive milliseconds.

6. **Next timestamp.** Use `webhooks.time_utils.add_milliseconds` with the parsed `now_iso` instant. Do not truncate to whole seconds.

### Audit block

Populate `audit` with:

```python
{
    "exponential_delay_ms": int,          # value after backoff + Retry-After, before jitter
    "retry_after_applied_ms": int | None, # retry_after_seconds * 1000 if provided else None
    "jitter_factor": str,                 # four-decimal string from deterministic_jitter
    "capped": bool,                       # True iff raw exponential (before Retry-After) hit max_delay_ms
}
```

## Self-check examples (visible tests)

Use these to validate locally with `pytest /tests/test_visible.py` (the full verifier also runs hidden cases):

**Policy defaults for all examples:** `base_delay_ms=1000`, `multiplier=2.0`, `max_delay_ms=10000`, `jitter_ratio=0.2`, `max_attempts=4`.

| Scenario | Inputs | Expected highlights |
|----------|--------|---------------------|
| First failure | `delivery_id="wh_abc123"`, `failed_attempt=1`, `now_iso="2026-03-01T00:00:00Z"` | `attempt_number=2`, `delay_ms=916`, `next_attempt_at="2026-03-01T00:00:00.916Z"`, `status="scheduled"` |
| Second failure | same id, `failed_attempt=2` | `attempt_number=3`, `delay_ms=1684` |
| Period boundary | `failed_attempt=1`, `now_iso="2026-03-01T00:00:00Z"` | `audit["exponential_delay_ms"] == 1000` |
| Dead letter | `failed_attempt=4` | `exhausted=True`, `status="dead_letter"`, `next_attempt_at is None` |

## Constraints

- Edit **only** `/app/webhooks/scheduler.py`.
- Do not change function signatures or import paths used by the verifier.
- Do not hard-code test expectations; the grading suite imports your module dynamically.

## Done when

`compute_schedule` satisfies the contract above and passes both the visible and hidden verifier suites.
