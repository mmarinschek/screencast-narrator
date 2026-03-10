"""Python client for screencast-narrator: record narrated screencasts from browser automation."""

from screencast_narrator_client.generated import (
    HighlightStyle,
    ScreenActionTiming,
    ScreenActionType,
)
from screencast_narrator_client.highlight import draw_highlight, highlight, remove_highlight
from screencast_narrator_client.shared_config import (
    HighlightConfig,
    RecordingConfig,
    SharedConfig,
    load_shared_config,
)
from screencast_narrator_client.storyboard import (
    Narration,
    ScreenAction,
    Storyboard,
)

__all__ = [
    "HighlightConfig",
    "HighlightStyle",
    "RecordingConfig",
    "SharedConfig",
    "load_shared_config",
    "Narration",
    "ScreenAction",
    "ScreenActionTiming",
    "ScreenActionType",
    "Storyboard",
    "draw_highlight",
    "highlight",
    "remove_highlight",
]
