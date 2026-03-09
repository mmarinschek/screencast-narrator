"""QR code sync frame injection: generates QR overlay JS snippets for browser-based recording."""

from __future__ import annotations

import base64
import io
import json
import logging
import math

import qrcode
from PIL import Image

from screencast_narrator_client.shared_config import (
    MarkerPosition,
    SharedConfig,
    SyncFrameConfig,
    SyncMarkers,
)

log = logging.getLogger(__name__)

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    _HAS_PYZBAR = True
except ImportError:
    _HAS_PYZBAR = False

_MAX_INJECT_RETRIES = 3

MAX_QR_DATA_LENGTH: int = 2000
_CONTINUATION_OVERHEAD: int = 30


def _escape_js_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n")


class SyncFrameInjector:
    def __init__(
        self,
        config: SharedConfig,
        display_duration_ms: int | None = None,
        post_removal_gap_ms: int | None = None,
    ) -> None:
        self._sf: SyncFrameConfig = config.sync_frame
        self._sm: SyncMarkers = config.sync_markers
        self._display_duration_ms = display_duration_ms if display_duration_ms is not None else self._sf.display_duration_ms
        self._post_removal_gap_ms = post_removal_gap_ms if post_removal_gap_ms is not None else self._sf.post_removal_gap_ms

    def format_init_data(
        self,
        language: str,
        debug_overlay: bool = False,
        font_size: int = 24,
        voices: dict[str, dict[str, str]] | None = None,
    ) -> str:
        payload: dict = {"t": self._sm.init.value, "language": language}
        if debug_overlay:
            payload["debugOverlay"] = True
        if font_size != 24:
            payload["fontSize"] = font_size
        if voices:
            payload["voices"] = voices
        return json.dumps(payload, separators=(",", ":"))

    def format_sync_data(
        self,
        narration_id: int,
        marker: MarkerPosition,
        text: str = "",
        translations: dict[str, str] | None = None,
        voice: str | None = None,
    ) -> str:
        payload: dict = {"t": self._sm.narration.value, "id": narration_id, "m": marker.value}
        if text:
            payload["tx"] = text
        if translations:
            payload["tr"] = translations
        if voice:
            payload["vc"] = voice
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

    def format_done_data(self) -> str:
        return json.dumps({"t": self._sm.done.value}, separators=(",", ":"))

    def inject_done_frame(self, page) -> None:
        saved_display = self._display_duration_ms
        self._display_duration_ms = self._sf.done_display_duration_ms
        self._inject_qr_overlay(page, self.format_done_data())
        self._display_duration_ms = saved_display

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

    def inject_init_frame(
        self,
        page,
        language: str,
        debug_overlay: bool = False,
        font_size: int = 24,
        voices: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self._inject_qr_overlay(page, self.format_init_data(language, debug_overlay, font_size, voices))

    def inject_sync_frame(
        self,
        page,
        narration_id: int,
        marker: MarkerPosition,
        text: str = "",
        translations: dict[str, str] | None = None,
        voice: str | None = None,
    ) -> None:
        self._inject_qr_overlay(page, self.format_sync_data(narration_id, marker, text, translations, voice))

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

    def _inject_single_qr(self, page, data: str, label: str = "") -> None:
        data_url = self.generate_qr_data_url(data)
        js = self._sf.resolved_inject_js.replace("{{dataUrl}}", data_url).replace("{{label}}", _escape_js_string(label))

        for attempt in range(_MAX_INJECT_RETRIES):
            page.evaluate(js)

            verified = self._verify_qr_visible(page, data)
            if verified:
                break

            log.error(
                "Sync frame NOT visible after injection (attempt %d/%d, data=%s). Retrying...",
                attempt + 1, _MAX_INJECT_RETRIES, data[:80],
            )
            page.evaluate(self._sf.remove_js)
            page.wait_for_timeout(100)
        else:
            raise RuntimeError(
                f"Sync frame not visible after {_MAX_INJECT_RETRIES} retries (data={data[:80]}). "
                f"The overlay could not be rendered on this page."
            )

        page.wait_for_timeout(self._display_duration_ms)
        page.evaluate(self._sf.remove_js)
        page.wait_for_timeout(self._post_removal_gap_ms)

    def _verify_qr_visible(self, page, expected_data: str) -> bool:
        screenshot_bytes = page.screenshot()
        img = Image.open(io.BytesIO(screenshot_bytes))

        w, h = img.size
        margin_x, margin_y = max(1, w // 10), max(1, h // 10)
        sample_points = [
            (margin_x, margin_y), (w - 1 - margin_x, margin_y),
            (margin_x, h - 1 - margin_y), (w - 1 - margin_x, h - 1 - margin_y),
        ]
        green_count = 0
        for sx, sy in sample_points:
            r, g, b = img.getpixel((sx, sy))[:3]
            if g > 180 and (g - r) > 80 and (g - b) > 80:
                green_count += 1
        if green_count < 3:
            log.debug("Green check failed: only %d/4 corners are green", green_count)
            return False

        if not _HAS_PYZBAR:
            return True

        results = pyzbar_decode(img)
        if not results:
            bw = img.convert("L").point(lambda x: 255 if x > 128 else 0)
            results = pyzbar_decode(bw)
        if not results:
            log.debug("QR decode failed on screenshot despite green background")
            return False

        decoded = results[0].data.decode("utf-8")
        if decoded != expected_data:
            log.debug("QR mismatch: expected %s, got %s", expected_data[:50], decoded[:50])
            return False

        return True

    def _inject_qr_overlay(self, page, data: str) -> None:
        frames = split_into_continuation_frames(data)
        for i, frame in enumerate(frames):
            label = data if i == 0 else f"(cont {i + 1}/{len(frames)})"
            self._inject_single_qr(page, frame, label)


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
