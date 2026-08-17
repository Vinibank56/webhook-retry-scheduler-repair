# Odyssey Authoring Notes (Future Projects)

Lessons from `webhook-retry-scheduler-repair`. Keep this file in the GitHub repo; it is excluded from the Odyssey upload ZIP.

---

## 1. ZIP bundle structure (critical)

**Odyssey rejects bundles where required files are nested inside a folder.**

| Wrong | Correct |
|-------|---------|
| `my-task/task.toml` | `task.toml` |
| `my-task/tests/test.sh` | `tests/test.sh` |

When building the ZIP, place `task.toml`, `instruction.md`, `environment/`, `tests/`, and `solution/` at the **archive root**, not inside a wrapper directory.

---

## 2. task.toml requirements

- Include `[metadata] name = "your-slug"` (not only `[task] name`).
- Include `version = "1.0"` and `schema_version = "1.0"`.
- Align `[environment]` resources with the draft form (bundle may request **less**, never more).
- Set `[agent] network_mode = "none"` and `[verifier] network_mode = "none"` for offline tasks.

---

## 3. Verification design

### Visible / hidden split
- **Visible** (`test_visible.py`): document 3–5 self-check cases in `instruction.md`.
- **Hidden** (`test_hidden.py`): edge cases, unpublished inputs, policy variants.

### Behavior over implementation
- Add `tests/spec_reference.py` — sealed canonical implementation of the contract.
- Add `tests/invariants.py` — objective properties (e.g. `now + delay_ms == next_attempt_at`).
- Parametrize hidden tests with **unpublished delivery IDs** compared against the spec reference to block hard-coding.

### Anti-gaming checklist
- [ ] Unpublished inputs in hidden tests only
- [ ] Sealed spec reference the agent cannot read at runtime
- [ ] Invariant checks independent of literal values
- [ ] Audit/metadata fields verified separately from top-level outputs
- [ ] Input validation tests (invalid timestamps, failed_attempt bounds)

---

## 4. instruction.md

- State the **background** and why the task matters.
- Document the full contract (API, rules, audit schema, invariants).
- Provide self-check examples for visible tests only.
- Explicitly warn that hidden tests use unpublished inputs.
- Tell the agent which files are correct and must not be edited.

---

## 5. Reference solution

- `solution/solve.sh` must run the **full** verifier (visible + hidden), not just visible.
- Reference code should mirror instruction rules with brief comments mapping to each rule.
- Verify locally: broken seed fails; reference passes 100%.

---

## 6. Draft form alignment

Ensure draft fields match the bundle:

| Draft field | Bundle source |
|-------------|---------------|
| resourceEstimate | `task.toml` `[environment]` + timeouts |
| oracleStrategy | How `solution/solve.sh` works |
| verificationStrategy | Visible/hidden split + invariant strategy |
| anticipatedExploits | Every shortcut + how verifier blocks it |
| difficultyExplanation | Specific traps, not "it's hard" |

---

## 7. Pre-submission checklist

- [ ] ZIP root contains `task.toml` directly (not nested)
- [ ] All 5 required paths present
- [ ] Broken seed fails verifier (nop floor)
- [ ] Reference solution passes all tests (oracle)
- [ ] Shell scripts use LF line endings
- [ ] No `.pytest_cache` or stray files in ZIP
- [ ] Draft form filled; resources aligned with `task.toml`

---

## 8. GitHub backup

Push the task folder as a private repo after bundle passes inspection. Include `AUTHORING_NOTES.md` and draft helpers; exclude `.pytest_cache` via `.gitignore`.

Repository: https://github.com/Vinibank56/webhook-retry-scheduler-repair
