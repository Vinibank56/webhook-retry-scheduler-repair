#!/usr/bin/env bash
# Reference implementation for webhook-retry-scheduler-repair.
#
# Installs the spec-compliant scheduler and validates the full verifier suite
# (visible, hidden edge cases, and behavioral property tests) before grading.
set -euo pipefail

cp /solution/scheduler.py /app/webhooks/scheduler.py

python3 -m pytest \
  /tests/test_visible.py \
  /tests/test_hidden.py \
  /tests/test_behavior_hidden.py \
  -q
