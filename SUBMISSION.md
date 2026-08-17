# Odyssey Submission Package — webhook-retry-scheduler-repair

**Author:** Vincent Onuegbunam (`onuegbunamvincent@gmail.com`)

---

## Files in this folder

| File | Purpose |
|------|---------|
| `draft.json` | All draft form field values (machine-readable) |
| `DRAFT.md` | Same draft fields in readable markdown |
| `webhook-retry-scheduler-repair.zip` | Upload this to Odyssey (in parent folder) |
| `task.toml`, `instruction.md`, etc. | Unpacked bundle source |

---

## Submission steps

### Step 1 — Create the draft (Odyssey web app)

1. Log in to **Odyssey** and open **My tasks** → **Start a submission** (or create a new draft).
2. Copy each field from `draft.json` or the table below into the draft form.
3. **Save the draft** before uploading the bundle.

### Step 2 — Upload the bundle

1. From your saved draft, click **Request upload URL**.
2. Upload **`webhook-retry-scheduler-repair.zip`** (located in the parent `odyssey project` folder).
3. Wait for inspection → **safe** → automatic submission to the funnel.

### Step 3 — Monitor funnel

Watch on your task page: Structure → Similarity → Oracle & nop → Quality check → Difficulty probe → Synthesis.

---

## Draft form — copy/paste values

### Task identity

- **title:** Repair Webhook Retry Scheduler
- **workingSlug:** webhook-retry-scheduler-repair
- **collectionFamily:** Product clone
- **taskFamily:** debugging
- **verifierFamily:** programmatic

### What the task is

**objective:**
```
Fix the broken webhook delivery retry scheduler in `/app/webhooks/scheduler.py`. After a failed delivery attempt, the service must compute the next retry timestamp using exponential backoff with a deterministic jitter factor, honor HTTP `Retry-After` floors when provided, cap delays at `max_delay_ms`, and dead-letter deliveries once `failed_attempt >= max_attempts`. The agent may edit only `scheduler.py`; companion modules (`policy.py`, `jitter.py`, `time_utils.py`) are correct. Done means `compute_schedule` returns the documented dict shape and passes the sealed pytest verifier (visible self-check cases plus held-out hidden cases).
```

**motivation:**
```
Webhook platforms schedule millions of retries daily. A subtly wrong scheduler causes thundering herds (missing jitter), SLA breaches (ignored Retry-After), or infinite retry loops (off-by-one exhaustion). This task mirrors on-call work triaging a production retry engine where multiple independent bugs stack together — exactly the kind of reasoning frontier agents must demonstrate.
```

### Difficulty & effort

**difficultyExplanation:**
```
Difficulty concentrates in reconciling six interacting rules that each look plausible in isolation: (1) dead-letter when `failed_attempt >= max_attempts` vs `>`; (2) exponent uses `failed_attempt - 1` so the first retry waits one base interval; (3) jitter is multiplicative via `deterministic_jitter`, not additive milliseconds; (4) `Retry-After` raises the pre-jitter delay floor; (5) raw exponential must cap at `max_delay_ms` before jitter; (6) timestamps must preserve millisecond precision via `add_milliseconds`. The seed code passes superficial shape checks and even returns plausible-looking delays, so agents that patch only one bug still fail held-out cases. Hidden tests additionally verify audit metadata (`capped`, `retry_after_applied_ms`) and sub-second timestamp preservation — fields agents often omit when hard-coding visible examples.
```

**expertTimeEstimateHours:** `2.5`

### Environment & resources

**environmentSummary:**
```
Python 3.11 (bookworm) container with `/app` as the working tree. Pre-installed: `pytest`, `bash`, `curl`. The app is a small webhook delivery package under `/app/webhooks/` containing a broken `scheduler.py` plus correct helpers for policy parsing, SHA-256 deterministic jitter, and UTC millisecond time arithmetic. No database, no network services, no runtime package installs — the agent reads `instruction.md`, inspects the modules, and patches `scheduler.py` in place. Verifier tests live under `/tests/` and import the agent's module dynamically from `/app`.
```

**resourceEstimate:**

| Field | Value |
|-------|-------|
| cpuMillis | 2000 |
| memoryMb | 2048 |
| storageMb | 4096 |
| gpuCount | 0 |
| agentTimeoutSec | 7200 |
| verifierTimeoutSec | 600 |

**networkRequirements:**

- **mode:** none
- **justification:** Fully offline debugging task; all dependencies baked into the Docker image at build time.

### Oracle & verification

**oracleStrategy:**
```
solution/solve.sh copies the reference scheduler.py into /app/webhooks/scheduler.py, replacing the seed implementation with a spec-compliant version that: dead-letters at failed_attempt >= max_attempts; computes raw_exponential = base * multiplier ** (failed_attempt - 1) and caps it; applies Retry-After as a floor; multiplies by (1 + jitter_factor) from deterministic_jitter; and formats the next timestamp with millisecond precision via add_milliseconds + format_instant. The script smoke-runs visible tests before the harness grades the full suite.
```

**verificationStrategy:**
```
tests/test.sh runs pytest over two modules: test_visible.py (5 cases — result shape, first/second failure delays, dead-letter on attempt 4, input validation) mirrors the self-check table in instruction.md so agents can iterate locally; test_hidden.py (8 cases — third-failure exponential step, Retry-After dominance, max-delay cap with audit flag, boundary scheduling on attempt 3, multiplicative jitter proof via two-step delivery, sub-second timestamp preservation, dead-letter not one attempt late, audit null for absent Retry-After) is held out. Scoring is binary (all pass → reward 1). Checks span functional outputs, audit invariants, error handling, and timestamp precision — no single channel is sufficient to pass alone.
```

### Scoring & exploits

**binarySuccessCondition:**
```
All pytest cases in test_visible.py and test_hidden.py pass when importing compute_schedule from /app/webhooks/scheduler.py.
```

**partialScoreStrategy:**
```
Binary scoring only — no partial credit. This keeps grading deterministic and prevents agents from satisfying a subset of audit fields while leaving core timing logic broken.
```

**anticipatedExploits:**
```
1. Hard-coding visible expectations — defeated by hidden deliveries (wh_retry01, wh_cap001, wh_edge99) with different jitter hashes and Retry-After/cap scenarios not listed in instruction.md. 2. Patching only dead-letter off-by-one — hidden tests still fail on jitter math, Retry-After floors, and millisecond timestamps. 3. Replacing jitter with randomness — tests assert exact deterministic factors from SHA-256; non-deterministic jitter fails immediately. 4. Editing helper modules — verifier imports agent code from /app/webhooks/ only; modifying tests is impossible (sealed mount); copying test literals into scheduler without general logic fails hidden parameter combinations. 5. Using floating-second timedelta — sub-second now_iso inputs expose truncation; hidden case requires .123Z preservation in output. 6. Ignoring audit block — hidden tests assert capped, retry_after_applied_ms, and formatted jitter_factor strings independently of top-level delay fields.
```

---

## Bundle contents (inside ZIP)

```
webhook-retry-scheduler-repair/
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile
│   └── app/webhooks/...
├── tests/
│   ├── test.sh
│   ├── test_visible.py
│   ├── test_hidden.py
│   └── helpers.py
└── solution/
    ├── solve.sh
    └── scheduler.py
```

## Pre-upload checklist

- [x] All required paths present
- [x] Broken seed fails verifier (9/13 fail)
- [x] Reference solution passes verifier (13/13 pass)
- [x] Agent network_mode = none in task.toml
- [x] Resource limits within sandbox budget
- [x] No .pytest_cache or stray files in ZIP
