"""Shared configuration — re-exports from screencast_narrator_client."""

from screencast_narrator_client.generated import MarkerPosition, SyncType
from screencast_narrator_client.shared_config import (
    HighlightConfig,
    SharedConfig,
    SyncFrameConfig,
    SyncMarkers,
    load_shared_config,
)

__all__ = [
    "HighlightConfig",
    "MarkerPosition",
    "SharedConfig",
    "SyncFrameConfig",
    "SyncMarkers",
    "SyncType",
    "load_shared_config",
]
