"""Shared helpers for webhook scheduler verifier tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def app_root() -> Path:
    if Path("/app").exists():
        return Path("/app")
    return Path(__file__).resolve().parents[1] / "environment" / "app"


def load_scheduler():
    root = str(app_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    for module_name in (
        "webhooks.scheduler",
        "webhooks.policy",
        "webhooks.jitter",
        "webhooks.time_utils",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]
    return importlib.import_module("webhooks.scheduler")


def default_policy():
    from webhooks.policy import default_policy as _default_policy

    return _default_policy()
