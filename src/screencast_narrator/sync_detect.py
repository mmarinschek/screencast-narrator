"""Sync frame detection: find green QR overlay frames in video and decode them."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

from screencast_narrator.shared_config import load_shared_config
from screencast_narrator_client.generated.storyboard_types import (
    ScreenAction,
    ScreenActionTiming,
    ScreenActionType,
)

_SM = load_shared_config().sync_markers


@dataclass(frozen=True)
class SyncMarker:
    sync_type: str
    entity_id: int
    marker: str
    frame_index: int


@dataclass(frozen=True)
class SyncFrameSpan:
    sync_type: str
    entity_id: int
    marker: str
    first_frame: int
    last_frame: int


@dataclass(frozen=True)
class SyncDetectionResult:
    qr_spans: list[SyncFrameSpan]
    green_frame_indices: set[int]
    total_frames: int
    narration_texts: dict[int, str] = field(default_factory=dict)
    narration_translations: dict[int, dict[str, str]] = field(default_factory=dict)
    screen_actions: dict[int, ScreenAction] = field(default_factory=dict)
    init_data: dict = field(default_factory=dict)


def is_green_frame(img: Image.Image) -> bool:
    w, h = img.size
    margin_x = max(1, w // 10)
    margin_y = max(1, h // 10)
    sample_x = [margin_x, w // 4, w // 2, 3 * w // 4, w - 1 - margin_x]
    sample_y = [margin_y, h // 4, h // 2, 3 * h // 4, h - 1 - margin_y]
    green_count = 0
    total = 0
    for sx in sample_x:
        for sy in sample_y:
            if sx == w // 2 and sy == h // 2:
                continue
            total += 1
            r, g, b = img.getpixel((sx, sy))[:3]
            if r < 80 and g > 180 and b < 80:
                green_count += 1
    return green_count >= total * 3 // 4


def decode_qr(img: Image.Image, frame_index: int) -> str:
    results = pyzbar_decode(img)
    if not results:
        raise RuntimeError(
            f"QR decode failed on green frame {frame_index} ({frame_index * 0.04:.3f}s). "
            f"Every green frame MUST contain a readable QR code."
        )
    return results[0].data.decode("utf-8")


def _parse_qr_payload(decoded: str) -> dict:
    return json.loads(decoded)


def detect_sync_frames(video_path: Path, temp_dir: Path) -> SyncDetectionResult:
    from screencast_narrator.ffmpeg import exec_ffmpeg

    frames_dir = temp_dir / "sync_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    exec_ffmpeg("-y", "-i", str(video_path), "-r", "25", str(frames_dir / "frame_%06d.png"))

    frame_paths = sorted(frames_dir.glob("*.png"))

    markers: list[SyncMarker] = []
    green_frame_indices: set[int] = set()
    narration_texts: dict[int, str] = {}
    narration_translations: dict[int, dict[str, str]] = {}
    screen_actions: dict[int, ScreenAction] = {}
    init_data: dict = {}

    continuation_buffer: list[str | None] = []
    continuation_total: int = 0
    init_seen = False

    for i, frame_path in enumerate(frame_paths):
        img = Image.open(frame_path)
        if not is_green_frame(img):
            if continuation_buffer:
                continuation_buffer = []
                continuation_total = 0
            continue

        green_frame_indices.add(i)
        decoded = decode_qr(img, i)
        payload = _parse_qr_payload(decoded)

        if "_c" in payload:
            seq, total = payload["_c"]
            if seq == 0:
                continuation_buffer = [None] * total
                continuation_total = total
            if continuation_total == total and seq < len(continuation_buffer):
                continuation_buffer[seq] = payload["d"]
            if all(c is not None for c in continuation_buffer):
                full_json = "".join(continuation_buffer)  # type: ignore[arg-type]
                payload = _parse_qr_payload(full_json)
                continuation_buffer = []
                continuation_total = 0
            else:
                continue

        sync_type = payload["t"]
        if sync_type not in _SM.all_types:
            raise RuntimeError(f"Green frame {i} ({i * 0.04:.3f}s) has unknown type: {sync_type}")

        if sync_type == _SM.init:
            init_data = payload
            init_seen = True
            continue

        if not init_seen:
            raise RuntimeError(
                f"Sync frame at frame {i} ({i * 0.04:.3f}s) appeared before the init frame. "
                f"The init frame must be the first sync frame in the video. "
                f"Make sure Storyboard is initialized before any narration or screen action begins."
            )

        entity_id = payload["id"]
        marker_type = payload["m"]

        if sync_type == _SM.narration and marker_type == _SM.start:
            if "tx" in payload:
                narration_texts[entity_id] = payload["tx"]
            if "tr" in payload:
                narration_translations[entity_id] = payload["tr"]

        if sync_type == _SM.action and marker_type == _SM.start:
            st_raw = payload.get("st")
            tm_raw = payload.get("tm")
            screen_actions[entity_id] = ScreenAction(
                type=ScreenActionType(st_raw) if st_raw else ScreenActionType.navigate,
                screen_action_id=entity_id,
                description=payload.get("desc"),
                timing=ScreenActionTiming(tm_raw) if tm_raw else None,
                duration_ms=payload.get("dur"),
            )

        if sync_type == _SM.highlight and marker_type == _SM.start:
            screen_actions[entity_id] = ScreenAction(
                type=ScreenActionType.highlight,
                screen_action_id=entity_id,
            )

        markers.append(SyncMarker(sync_type, entity_id, marker_type, i))

    spans = group_into_spans(markers)
    return SyncDetectionResult(
        spans, green_frame_indices, len(frame_paths),
        narration_texts, narration_translations, screen_actions, init_data,
    )


def group_into_spans(markers: list[SyncMarker]) -> list[SyncFrameSpan]:
    if not markers:
        return []
    spans: list[SyncFrameSpan] = []
    first = markers[0]
    span_first = first.frame_index
    span_last = first.frame_index
    span_sync_type = first.sync_type
    span_entity_id = first.entity_id
    span_marker = first.marker

    for m in markers[1:]:
        if (
            m.sync_type == span_sync_type
            and m.entity_id == span_entity_id
            and m.marker == span_marker
            and m.frame_index <= span_last + 2
        ):
            span_last = m.frame_index
        else:
            spans.append(SyncFrameSpan(span_sync_type, span_entity_id, span_marker, span_first, span_last))
            span_first = m.frame_index
            span_last = m.frame_index
            span_sync_type = m.sync_type
            span_entity_id = m.entity_id
            span_marker = m.marker

    spans.append(SyncFrameSpan(span_sync_type, span_entity_id, span_marker, span_first, span_last))
    return spans


def strip_sync_frames(video_path: Path, green_frame_indices: set[int], temp_dir: Path) -> Path:
    from screencast_narrator.ffmpeg import exec_ffmpeg

    if not green_frame_indices:
        return video_path

    cfr_video = temp_dir / "cfr_video.mp4"
    exec_ffmpeg(
        "-y",
        "-i",
        str(video_path),
        "-r",
        "25",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-an",
        str(cfr_video),
    )

    ranges = group_consecutive_into_ranges(green_frame_indices)
    between_clauses = "+".join(f"between(n\\,{r[0]}\\,{r[1]})" for r in ranges)
    select_filter = f"select='not({between_clauses})',setpts=N/25/TB"

    stripped_video = temp_dir / "stripped.mp4"
    exec_ffmpeg(
        "-y",
        "-i",
        str(cfr_video),
        "-vf",
        select_filter,
        "-r",
        "25",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-an",
        str(stripped_video),
    )

    return stripped_video


def group_consecutive_into_ranges(indices: set[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    range_start = -1
    range_end = -1
    for idx in sorted(indices):
        if range_start == -1:
            range_start = idx
            range_end = idx
        elif idx == range_end + 1:
            range_end = idx
        else:
            ranges.append((range_start, range_end))
            range_start = idx
            range_end = idx
    if range_start != -1:
        ranges.append((range_start, range_end))
    return ranges


def build_sync_position_map(spans: list[SyncFrameSpan], green_frame_indices: set[int]) -> dict[str, float]:
    sorted_spans = sorted(spans, key=lambda s: s.first_frame)
    sorted_green = sorted(green_frame_indices)

    positions: dict[str, float] = {}
    for span in sorted_spans:
        green_before = _count_less_than(sorted_green, span.first_frame)
        adjusted_position_s = (span.first_frame - green_before) * 0.04
        key = f"{span.sync_type}{_SM.separator}{span.entity_id}{_SM.separator}{span.marker}"
        positions[key] = adjusted_position_s
    return positions


def _count_less_than(sorted_list: list[int], value: int) -> int:
    lo, hi = 0, len(sorted_list)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_list[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return lo
