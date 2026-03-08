"""Shared configuration loaded from api/common/config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from screencast_narrator_client.generated.qr_payload_types import MarkerPosition, SyncType


@dataclass(frozen=True)
class SyncMarkers:
    init: SyncType
    narration: SyncType
    action: SyncType
    highlight: SyncType
    separator: str
    start: MarkerPosition
    end: MarkerPosition

    def key(self, sync_type: SyncType, entity_id: int, marker: MarkerPosition) -> str:
        return f"{sync_type.value}{self.separator}{entity_id}{self.separator}{marker.value}"

    def narration_start(self, narration_id: int) -> str:
        return self.key(self.narration, narration_id, self.start)

    def narration_end(self, narration_id: int) -> str:
        return self.key(self.narration, narration_id, self.end)

    def action_start(self, action_id: int) -> str:
        return self.key(self.action, action_id, self.start)

    def action_end(self, action_id: int) -> str:
        return self.key(self.action, action_id, self.end)

    def highlight_start(self, highlight_id: int) -> str:
        return self.key(self.highlight, highlight_id, self.start)

    def highlight_end(self, highlight_id: int) -> str:
        return self.key(self.highlight, highlight_id, self.end)

    @property
    def all_types(self) -> tuple[SyncType, ...]:
        return (self.init, self.narration, self.action, self.highlight)


@dataclass(frozen=True)
class SyncFrameConfig:
    qr_size: int
    display_duration_ms: int
    post_removal_gap_ms: int
    inject_js: str
    remove_js: str


@dataclass(frozen=True)
class HighlightConfig:
    scroll_wait_ms: int
    draw_wait_ms: int
    remove_wait_ms: int
    color: str
    padding: int
    animation_speed_ms: int
    line_width_min: int
    line_width_max: int
    opacity: float
    segments: int
    coverage: float
    scroll_js: str
    scroll_wait_js: str
    draw_js: str
    remove_js: str

    @property
    def resolved_draw_js(self) -> str:
        return (
            self.draw_js
            .replace("{{padding}}", str(self.padding))
            .replace("{{lineWidthMin}}", str(self.line_width_min))
            .replace("{{lineWidthMax}}", str(self.line_width_max))
            .replace("{{opacity}}", str(self.opacity))
            .replace("{{segments}}", str(self.segments))
            .replace("{{coverage}}", str(self.coverage))
            .replace("{{animationSpeedMs}}", str(self.animation_speed_ms))
            .replace("{{color}}", self.color)
        )


@dataclass(frozen=True)
class SharedConfig:
    sync_markers: SyncMarkers
    sync_frame: SyncFrameConfig
    highlight: HighlightConfig


def _find_config_path() -> Path:
    candidate = Path(__file__).resolve().parent.parent.parent.parent / "common" / "config.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"api/common/config.json not found at {candidate}. "
        f"Ensure you are running from a repository checkout."
    )


def _resolve_js(config_dir: Path, value: str) -> str:
    js_path = config_dir / value
    if js_path.exists():
        return js_path.read_text(encoding="utf-8").strip()
    return value


def load_shared_config() -> SharedConfig:
    config_path = _find_config_path()
    config_dir = config_path.parent
    data = json.loads(config_path.read_text(encoding="utf-8"))

    sm = data["syncMarkers"]
    sf = data["syncFrame"]
    hl = data["highlight"]

    return SharedConfig(
        sync_markers=SyncMarkers(
            init=SyncType(sm["init"]),
            narration=SyncType(sm["narration"]),
            action=SyncType(sm["action"]),
            highlight=SyncType(sm["highlight"]),
            separator=sm["separator"],
            start=MarkerPosition(sm["start"]),
            end=MarkerPosition(sm["end"]),
        ),
        sync_frame=SyncFrameConfig(
            qr_size=sf["qrSize"],
            display_duration_ms=sf["displayDurationMs"],
            post_removal_gap_ms=sf["postRemovalGapMs"],
            inject_js=_resolve_js(config_dir, sf["injectJs"]),
            remove_js=_resolve_js(config_dir, sf["removeJs"]),
        ),
        highlight=HighlightConfig(
            scroll_wait_ms=hl["scrollWaitMs"],
            draw_wait_ms=hl["drawWaitMs"],
            remove_wait_ms=hl["removeWaitMs"],
            color=hl["color"],
            padding=hl["padding"],
            animation_speed_ms=hl["animationSpeedMs"],
            line_width_min=hl["lineWidthMin"],
            line_width_max=hl["lineWidthMax"],
            opacity=hl["opacity"],
            segments=hl["segments"],
            coverage=hl["coverage"],
            scroll_js=_resolve_js(config_dir, hl["scrollJs"]),
            scroll_wait_js=_resolve_js(config_dir, hl["scrollWaitJs"]),
            draw_js=_resolve_js(config_dir, hl["drawJs"]),
            remove_js=_resolve_js(config_dir, hl["removeJs"]),
        ),
    )
