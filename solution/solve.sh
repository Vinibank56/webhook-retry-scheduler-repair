#!/usr/bin/env bash
# Oracle entrypoint: install reference implementation only.
# The harness runs tests/test.sh separately to grade reward.
set -euo pipefail

cp /solution/scheduler.py /app/webhooks/scheduler.py

exit 0
