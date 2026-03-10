"""Shared configuration loaded from api/common/config.json."""

from __future__ import annotations

import json
from pathlib import Path

from screencast_narrator_client.generated.config_types import (
    HighlightConfig,
    Model as ConfigModel,
    RecordingConfig,
)
from screencast_narrator_client.generated.storyboard_types import HighlightStyle


class SharedConfig:
    def __init__(self, model: ConfigModel, config_dir: Path) -> None:
        self._model = model
        self._config_dir = config_dir

    @property
    def recording(self) -> RecordingConfig:
        return self._model.recording

    @property
    def highlight(self) -> HighlightConfig:
        return self._model.highlight

    @property
    def resolved_scroll_js(self) -> str:
        return self._resolve_js(self.highlight.scroll_js)

    @property
    def resolved_scroll_wait_js(self) -> str:
        return self._resolve_js(self.highlight.scroll_wait_js)

    @property
    def resolved_draw_js(self) -> str:
        raw = self._resolve_js(self.highlight.draw_js)
        replacements = self.highlight.model_dump(by_alias=True)
        for key, value in replacements.items():
            raw = raw.replace("{{" + key + "}}", str(value))
        return raw

    @property
    def resolved_remove_js(self) -> str:
        return self._resolve_js(self.highlight.remove_js)

    def ffmpeg_args(self, output_file: str) -> list[str]:
        rec = self.recording
        return [
            "ffmpeg",
            "-loglevel", "error",
            "-f", "image2pipe",
            "-avioflags", "direct",
            "-fpsprobesize", "0",
            "-probesize", "32",
            "-analyzeduration", "0",
            "-c:v", "mjpeg",
            "-i", "pipe:0",
            "-y", "-an",
            "-r", str(rec.fps),
            "-c:v", str(rec.codec),
            "-preset", str(rec.preset),
            "-crf", str(rec.crf),
            "-pix_fmt", str(rec.pixel_format),
            "-threads", "1",
            output_file,
        ]

    def with_highlight_overrides(self, style: HighlightStyle) -> SharedConfig:
        hl = self.highlight
        overridden = HighlightConfig(
            scroll_wait_ms=style.scroll_wait_ms if style.scroll_wait_ms is not None else hl.scroll_wait_ms,
            draw_wait_ms=style.draw_duration_ms if style.draw_duration_ms is not None else hl.draw_wait_ms,
            remove_wait_ms=style.remove_wait_ms if style.remove_wait_ms is not None else hl.remove_wait_ms,
            color=style.color if style.color is not None else hl.color,
            padding=style.padding if style.padding is not None else hl.padding,
            animation_speed_ms=style.animation_speed_ms if style.animation_speed_ms is not None else hl.animation_speed_ms,
            line_width_min=style.line_width_min if style.line_width_min is not None else hl.line_width_min,
            line_width_max=style.line_width_max if style.line_width_max is not None else hl.line_width_max,
            opacity=style.opacity if style.opacity is not None else hl.opacity,
            segments=style.segments if style.segments is not None else hl.segments,
            coverage=style.coverage if style.coverage is not None else hl.coverage,
            scroll_js=hl.scroll_js,
            scroll_wait_js=hl.scroll_wait_js,
            draw_js=hl.draw_js,
            remove_js=hl.remove_js,
        )
        model = ConfigModel(recording=self.recording, highlight=overridden)
        return SharedConfig(model, self._config_dir)

    def _resolve_js(self, value: str) -> str:
        js_path = self._config_dir / value
        if js_path.exists():
            return js_path.read_text(encoding="utf-8").strip()
        return value


def _find_config_path() -> Path:
    candidate = Path(__file__).resolve().parent.parent.parent.parent / "common" / "config.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"api/common/config.json not found at {candidate}. "
        f"Ensure you are running from a repository checkout."
    )


def load_shared_config() -> SharedConfig:
    config_path = _find_config_path()
    config_dir = config_path.parent
    data = json.loads(config_path.read_text(encoding="utf-8"))
    model = ConfigModel.model_validate(data)
    return SharedConfig(model, config_dir)
