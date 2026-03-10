"""Shared configuration — re-exports from screencast_narrator_client."""

from screencast_narrator_client.shared_config import (
    HighlightConfig,
    RecordingConfig,
    SharedConfig,
    load_shared_config,
)

__all__ = [
    "HighlightConfig",
    "RecordingConfig",
    "SharedConfig",
    "load_shared_config",
]
