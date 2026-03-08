"""Storyboard — re-exports from screencast_narrator_client."""

from screencast_narrator_client.generated import HighlightStyle, ScreenActionTiming, ScreenActionType
from screencast_narrator_client.storyboard import (
    Narration,
    ScreenAction,
    Storyboard,
)

__all__ = [
    "HighlightStyle",
    "Narration",
    "ScreenAction",
    "ScreenActionTiming",
    "ScreenActionType",
    "Storyboard",
]
