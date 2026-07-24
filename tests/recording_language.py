"""Recording-language selection for e2e tests: random by default, forceable via env."""

from __future__ import annotations

import os
import random


def choose_recording_language(available: list[str]) -> str:
    """Pick the client language used for the recording phase.

    SCREENCAST_E2E_LANGUAGE forces a specific language (used by CI release
    workflows to deterministically exercise one client); otherwise one of the
    locally runnable languages is picked at random.
    """
    forced = os.environ.get("SCREENCAST_E2E_LANGUAGE")
    if forced:
        if forced not in available:
            raise RuntimeError(
                f"SCREENCAST_E2E_LANGUAGE={forced!r} requested but only {available} are runnable here"
            )
        return forced
    return random.choice(available)
