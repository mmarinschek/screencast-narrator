"""Python client for screencast-narrator: record narrated screencasts from browser automation."""

from screencast_narrator_client.generated import (
    MarkerPosition,
    ScreenActionTiming,
    ScreenActionType,
    SyncType,
)
from screencast_narrator_client.highlight import draw_highlight, highlight, remove_highlight
from screencast_narrator_client.shared_config import (
    HighlightConfig,
    SharedConfig,
    SyncFrameConfig,
    SyncMarkers,
    load_shared_config,
)
from screencast_narrator_client.storyboard import (
    Narration,
    ScreenAction,
    Storyboard,
)
from screencast_narrator_client.sync_frames import (
    MAX_QR_DATA_LENGTH,
    SyncFrameInjector,
    reassemble_continuation_frames,
    split_into_continuation_frames,
)

__all__ = [
    "HighlightConfig",
    "MarkerPosition",
    "SharedConfig",
    "SyncFrameConfig",
    "SyncMarkers",
    "SyncType",
    "load_shared_config",
    "Narration",
    "ScreenAction",
    "ScreenActionTiming",
    "ScreenActionType",
    "Storyboard",
    "MAX_QR_DATA_LENGTH",
    "SyncFrameInjector",
    "reassemble_continuation_frames",
    "split_into_continuation_frames",
    "draw_highlight",
    "highlight",
    "remove_highlight",
]
