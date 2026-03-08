"""QR code sync frame injection — re-exports from screencast_narrator_client."""

from screencast_narrator_client.sync_frames import (
    MAX_QR_DATA_LENGTH,
    SyncFrameInjector,
    reassemble_continuation_frames,
    split_into_continuation_frames,
)

__all__ = [
    "MAX_QR_DATA_LENGTH",
    "SyncFrameInjector",
    "reassemble_continuation_frames",
    "split_into_continuation_frames",
]
