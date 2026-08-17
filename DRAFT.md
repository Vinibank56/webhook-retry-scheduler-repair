# Odyssey Draft Fields — webhook-retry-scheduler-repair (v2)

Updated after quality-band improvements. Copy into the Odyssey draft form.

See `draft.json` for machine-readable values. Key changes in v2: stronger verification strategy, expanded anticipatedExploits, behavior-focused hidden tests.

---

## Task identity

| Field | Value |
|-------|-------|
| **title** | Repair Webhook Retry Scheduler |
| **workingSlug** | webhook-retry-scheduler-repair |
| **collectionFamily** | Product clone |
| **taskFamily** | debugging |
| **verifierFamily** | programmatic |

---

## Oracle & verification (updated)

**verificationStrategy:**
```
tests/test.sh runs pytest over test_visible.py (5 documented self-check cases plus shape/validation) and test_hidden.py (edge cases, behavioral invariants via invariants.py, and parametrized unpublished delivery IDs verified against sealed tests/spec_reference.py). Verification is behavior-focused — outputs must match the spec reference and satisfy timestamp consistency, dead-letter shape, and audit schema. Binary scoring.
```

**anticipatedExploits:**
```
1. Hard-coding visible delivery IDs — blocked by parametrized hidden tests with wh_unseen_* IDs verified against sealed spec_reference.py. 2. Patching only dead-letter off-by-one — hidden tests fail on jitter math, Retry-After floors, capped flag semantics, and millisecond timestamps. 3. Random jitter — tests assert exact SHA-256 deterministic factors. 4. Editing helpers or tests — agent cannot access sealed spec reference at runtime. 5. Truncating to whole seconds — sub-second now_iso inputs and invariant now+delay_ms==next_attempt_at expose this. 6. Ignoring audit block — capped, retry_after_applied_ms, and jitter_factor verified independently. 7. Retry-After incorrectly setting capped=True — dedicated hidden test asserts capped reflects pre-floor raw exponential only. 8. Stub function returning constants — unpublished parametrized cases with alternate multipliers and zero jitter fail immediately.
```

All other fields unchanged from v1 — see `draft.json`.
