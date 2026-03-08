"""Element highlighting — re-exports from screencast_narrator_client."""

from screencast_narrator_client.highlight import draw_highlight, highlight, remove_highlight
from screencast_narrator_client.shared_config import HighlightConfig

__all__ = [
    "HighlightConfig",
    "draw_highlight",
    "highlight",
    "remove_highlight",
]
