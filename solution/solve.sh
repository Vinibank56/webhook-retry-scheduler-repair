#!/usr/bin/env bash
set -euo pipefail

cp /solution/scheduler.py /app/webhooks/scheduler.py

python3 -m pytest /tests/test_visible.py -q
