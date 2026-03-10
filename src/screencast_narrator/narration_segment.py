"""Data types for the merge pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NarrationSegment:
    start_ms: int
    end_ms: int
    text: str
    audio_duration_ms: int
