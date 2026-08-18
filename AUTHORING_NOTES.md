# Odyssey Authoring Notes — High-Quality Band Playbook

Lessons from `webhook-retry-scheduler-repair`. Keep in the GitHub repo; **exclude from Odyssey ZIP**.

**Repo:** https://github.com/Vinibank56/webhook-retry-scheduler-repair

---

## A. Bundle & intake fixes (learned the hard way)

| Issue | Fix |
|-------|-----|
| `required file missing` rejection | ZIP must have `task.toml` at **archive root**, not inside `my-task/task.toml` |
| Missing metadata | Add `[metadata] name = "slug"` in `task.toml`, not only `[task] name` |
| `.git` in ZIP | Exclude `.git/`, `.pytest_cache/`, draft helper files from upload ZIP |
| Shell scripts on Windows | Normalize `.sh` files to LF + executable bit before zipping |

---

## B. Verification strategy excellence

### Visible / hidden split

| Layer | File | Purpose |
|-------|------|---------|
| **Visible** | `test_visible.py` | 3–5 self-check cases documented in `instruction.md` |
| **Hidden edge** | `test_hidden.py` | Unpublished IDs, cap/Retry-After semantics, validation |
| **Hidden behavior** | `test_behavior_hidden.py` | Properties: backoff progression, jitter bounds, anti-stub |

### Multi-channel verification

Use **multiple independent grading channels** — a lucky partial fix must still fail:

1. **Literal edge cases** — specific unpublished inputs with expected outputs
2. **Sealed spec reference** (`tests/spec_reference.py`) — canonical contract re-implementation
3. **Invariants** (`tests/invariants.py`) — e.g. `now + delay_ms == next_attempt_at`
4. **Behavioral properties** — exponential growth, jitter bounds, distinct outputs per delivery ID
5. **Audit semantics** — `capped`, `retry_after_applied_ms` verified separately from top-level fields
6. **Input validation** — invalid timestamps, boundary `failed_attempt`

### Example hidden behavioral tests (this project)

```python
def test_exponential_pre_jitter_doubles_each_failure(): ...  # actual backoff curve
def test_jitter_factor_within_policy_bounds(): ...           # not just one timestamp
def test_distinct_delivery_ids_produce_distinct_delays(): ... # anti hard-coded stub
def test_pre_jitter_reaches_cap_under_aggressive_multiplier(): ...  # stress cap
def test_reference_matches_on_randomized_unseen_matrix(): ...       # property matrix
```

### What NOT to add (stay realistic)

Do **not** bolt on unrelated concerns just to sound impressive:

- Concurrent load / thread safety — unless the task is explicitly multi-threaded
- Network partitions — unless the environment models networking
- Resource cleanup / memory profiling — unless the task allocates resources

Match verification to the **actual deliverable**. This scheduler task grades a pure function — behavioral backoff/jitter/cap tests are on-target; goroutine stress tests are not.

---

## C. Exploit prevention excellence

Document every exploit in `anticipatedExploits` with **attack + prevention**:

| Exploit | Prevention |
|---------|------------|
| **Hard-coded responses** | Parametrize unpublished `wh_unseen_*` / `wh_matrix_*` delivery IDs; compare to sealed `spec_reference.py` |
| **Mock / stub implementation** | Require distinct delays across delivery IDs; verify backoff progression across failures |
| **Timing manipulation** | Invariant: `next_attempt_at == now + delay_ms` (millisecond precision) |
| **Partial fixes** | Six independent bugs — hidden suite tests each rule separately |
| **Random jitter** | Assert exact SHA-256 deterministic factors |
| **Audit gaming** | Test `capped` independently from Retry-After floor |
| **Editing helpers** | Agent may only edit `scheduler.py`; spec lives in sealed `/tests/` |

---

## D. Task design excellence

- **Real-world relevance** — Base on production scenarios (webhook Retry-After compliance, dead-letter exhaustion).
- **Appropriate difficulty** — Multiple interacting sub-rules; seed looks plausible but is wrong in six places.
- **Novelty** — Specific contract + deterministic jitter hash + audit semantics, not a generic "implement retry" prompt.

---

## E. Documentation excellence (`instruction.md` template)

```markdown
## Background          — why the system exists (with simple architecture diagram)
## Requirements        — what "done" looks like (bullet criteria)
## API contract        — full spec
## Constraints         — files agent may/may not touch
## Success metrics     — how grading measures success (visible vs hidden)
## Self-check examples — visible tests only
```

Avoid over-prescriptive step-by-step fixes — describe the goal and contract, not line numbers to edit.

---

## F. Environment excellence

```toml
[environment]
cpus = 2              # match actual need; draft form may request equal or more
memory_mb = 2048
storage_mb = 4096
gpus = 0
network_mode = "none" # unless task truly needs egress

[agent]
network_mode = "none"

[verifier]
network_mode = "none"
```

- Bake all deps into `environment/Dockerfile` at build time.
- No runtime `pip install` for offline tasks.

---

## G. Reference solution excellence

```bash
#!/usr/bin/env bash
# Reference implementation for [task-name].
# Installs fix and runs FULL verifier (visible + hidden + behavioral).
set -euo pipefail
cp /solution/fix /app/...
python3 -m pytest /tests/test_visible.py /tests/test_hidden.py /tests/test_behavior_hidden.py -q
```

- Reference code maps comments to each instruction rule.
- Oracle must pass **100%**; broken seed must fail **substantially** (nop floor).

---

## H. Draft form alignment

| Draft field | Source |
|-------------|--------|
| `objective` / `motivation` | `instruction.md` Background + Requirements |
| `difficultyExplanation` | List specific traps, not "it's hard" |
| `verificationStrategy` | Visible/hidden/behavior + spec reference + invariants |
| `anticipatedExploits` | Table above — attack + prevention for each |
| `oracleStrategy` | What `solve.sh` does step by step |
| `resourceEstimate` | Must align with `task.toml` (bundle ≤ form) |

---

## I. Final quality checklist (pre-submission)

- [ ] Novel, real-world problem — not a re-skin or leetcode drill
- [ ] ZIP root layout correct (no wrapper folder, no `.git`)
- [ ] `[metadata] name` in `task.toml`
- [ ] Visible/hidden/behavior test split
- [ ] Sealed `spec_reference.py` + `invariants.py`
- [ ] Unpublished parametrized test inputs
- [ ] 8+ documented exploits with preventions
- [ ] `instruction.md` has Background, Requirements, Constraints, Success metrics
- [ ] Reference passes all tests; broken seed fails most tests
- [ ] `solve.sh` runs full verifier
- [ ] Draft form matches bundle resources and strategy fields
- [ ] Private GitHub backup with `AUTHORING_NOTES.md`

---

## J. Version history (this project)

| Version | Changes |
|---------|---------|
| v1 | Initial task bundle |
| v2 | ZIP root fix; `spec_reference.py`; `invariants.py`; expanded hidden tests |
| v3 | `test_behavior_hidden.py`; instruction Requirements/Success metrics; maximization playbook |

**Current ZIP:** `webhook-retry-scheduler-repair.zip` (28 tests: 5 visible + 16 hidden edge + 7 behavioral)
