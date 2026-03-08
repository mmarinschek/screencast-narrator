"""QR code sync frame injection: generates QR overlay JS snippets for browser-based recording."""

from __future__ import annotations

import base64
import io
import json
import math

import qrcode

from screencast_narrator_client.shared_config import (
    MarkerPosition,
    SharedConfig,
    SyncFrameConfig,
    SyncMarkers,
)

MAX_QR_DATA_LENGTH: int = 2000
_CONTINUATION_OVERHEAD: int = 30


class SyncFrameInjector:
    def __init__(self, config: SharedConfig) -> None:
        self._sf: SyncFrameConfig = config.sync_frame
        self._sm: SyncMarkers = config.sync_markers

    def format_init_data(self, language: str, debug_overlay: bool = False, font_size: int = 24) -> str:
        payload: dict = {"t": self._sm.init.value, "language": language}
        if debug_overlay:
            payload["debugOverlay"] = True
        if font_size != 24:
            payload["fontSize"] = font_size
        return json.dumps(payload, separators=(",", ":"))

    def format_sync_data(
        self,
        narration_id: int,
        marker: MarkerPosition,
        text: str = "",
        translations: dict[str, str] | None = None,
    ) -> str:
        payload: dict = {"t": self._sm.narration.value, "id": narration_id, "m": marker.value}
        if text:
            payload["tx"] = text
        if translations:
            payload["tr"] = translations
        return json.dumps(payload, separators=(",", ":"))

    def format_action_sync_data(
        self,
        screen_action_id: int,
        marker: MarkerPosition,
        description: str | None = None,
        screen_action_type: str | None = None,
        timing: str | None = None,
        duration_ms: int | None = None,
    ) -> str:
        payload: dict = {"t": self._sm.action.value, "id": screen_action_id, "m": marker.value}
        if description is not None:
            payload["desc"] = description
        if screen_action_type is not None and screen_action_type != "navigate":
            payload["st"] = screen_action_type
        if timing is not None and timing != "casted":
            payload["tm"] = timing
        if duration_ms is not None:
            payload["dur"] = duration_ms
        return json.dumps(payload, separators=(",", ":"))

    def format_highlight_sync_data(self, screen_action_id: int, marker: MarkerPosition) -> str:
        return json.dumps(
            {"t": self._sm.highlight.value, "id": screen_action_id, "m": marker.value},
            separators=(",", ":"),
        )

    def generate_qr_data_url(self, data: str) -> str:
        if len(data) > MAX_QR_DATA_LENGTH:
            raise ValueError(
                f"QR payload too large ({len(data)} chars, max {MAX_QR_DATA_LENGTH}). "
                f"Use split_into_continuation_frames() for large payloads."
            )
        qr_size = self._sf.qr_size
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((qr_size, qr_size))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    def inject_init_frame(self, page, language: str, debug_overlay: bool = False, font_size: int = 24) -> None:
        self._inject_qr_overlay(page, self.format_init_data(language, debug_overlay, font_size))

    def inject_sync_frame(
        self,
        page,
        narration_id: int,
        marker: MarkerPosition,
        text: str = "",
        translations: dict[str, str] | None = None,
    ) -> None:
        self._inject_qr_overlay(page, self.format_sync_data(narration_id, marker, text, translations))

    def inject_action_sync_frame(
        self,
        page,
        screen_action_id: int,
        marker: MarkerPosition,
        description: str | None = None,
        screen_action_type: str | None = None,
        timing: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self._inject_qr_overlay(
            page,
            self.format_action_sync_data(screen_action_id, marker, description, screen_action_type, timing, duration_ms),
        )

    def inject_highlight_sync_frame(self, page, screen_action_id: int, marker: MarkerPosition) -> None:
        self._inject_qr_overlay(page, self.format_highlight_sync_data(screen_action_id, marker))

    def _inject_single_qr(self, page, data: str) -> None:
        data_url = self.generate_qr_data_url(data)
        page.evaluate(self._sf.inject_js.replace("{{dataUrl}}", data_url))
        page.wait_for_timeout(self._sf.display_duration_ms)
        page.evaluate(self._sf.remove_js)
        page.wait_for_timeout(self._sf.post_removal_gap_ms)

    def _inject_qr_overlay(self, page, data: str) -> None:
        frames = split_into_continuation_frames(data)
        for frame in frames:
            self._inject_single_qr(page, frame)


def split_into_continuation_frames(data: str) -> list[str]:
    if len(data) <= MAX_QR_DATA_LENGTH:
        return [data]
    chunk_size = _find_chunk_size(data)
    total = math.ceil(len(data) / chunk_size)
    frames: list[str] = []
    for i in range(total):
        chunk = data[i * chunk_size : (i + 1) * chunk_size]
        wrapper = json.dumps({"_c": [i, total], "d": chunk}, separators=(",", ":"))
        frames.append(wrapper)
    return frames


def _find_chunk_size(data: str) -> int:
    chunk_size = MAX_QR_DATA_LENGTH - _CONTINUATION_OVERHEAD
    for _ in range(20):
        total = math.ceil(len(data) / chunk_size)
        test_chunk = data[:chunk_size]
        wrapper = json.dumps({"_c": [0, total], "d": test_chunk}, separators=(",", ":"))
        if len(wrapper) <= MAX_QR_DATA_LENGTH:
            return chunk_size
        chunk_size -= 50
    return chunk_size


def reassemble_continuation_frames(frames: list[str]) -> str:
    if len(frames) == 1:
        parsed = json.loads(frames[0])
        if "_c" not in parsed:
            return frames[0]
        return parsed["d"]
    parts: list[str] = []
    for frame in frames:
        parsed = json.loads(frame)
        parts.append(parsed["d"])
    return "".join(parts)
