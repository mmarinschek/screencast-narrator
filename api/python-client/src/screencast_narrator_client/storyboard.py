"""Storyboard: narration bracket and screen action recording for screencast narration."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from screencast_narrator_client.generated.storyboard_types import (
    HighlightStyle,
    Model as StoryboardModel,
    Narration,
    Options,
    ScreenAction,
    ScreenActionTiming,
    ScreenActionType,
)
from screencast_narrator_client.shared_config import SharedConfig, load_shared_config

log = logging.getLogger(__name__)


def _merge_highlight_styles(base: HighlightStyle, override: HighlightStyle) -> HighlightStyle:
    return HighlightStyle(
        color=override.color if override.color is not None else base.color,
        animation_speed_ms=override.animation_speed_ms if override.animation_speed_ms is not None else base.animation_speed_ms,
        draw_duration_ms=override.draw_duration_ms if override.draw_duration_ms is not None else base.draw_duration_ms,
        opacity=override.opacity if override.opacity is not None else base.opacity,
        padding=override.padding if override.padding is not None else base.padding,
        scroll_wait_ms=override.scroll_wait_ms if override.scroll_wait_ms is not None else base.scroll_wait_ms,
        remove_wait_ms=override.remove_wait_ms if override.remove_wait_ms is not None else base.remove_wait_ms,
        line_width_min=override.line_width_min if override.line_width_min is not None else base.line_width_min,
        line_width_max=override.line_width_max if override.line_width_max is not None else base.line_width_max,
        segments=override.segments if override.segments is not None else base.segments,
        coverage=override.coverage if override.coverage is not None else base.coverage,
    )


class Storyboard:
    def __init__(
        self,
        output_dir: Path,
        page=None,
        language: str = "en",
        highlight_style: HighlightStyle | None = None,
        debug_overlay: bool = False,
        font_size: int = 24,
        voices: dict[str, dict[str, str]] | None = None,
        video_width: int = 1280,
        video_height: int = 720,
    ) -> None:
        self._output_dir = output_dir
        self._page = page
        self._language = language
        self._config: SharedConfig = load_shared_config()
        self._highlight_style = highlight_style or HighlightStyle()
        self._debug_overlay_flag = debug_overlay
        self._font_size_val = font_size
        self._narrations: list[Narration] = []
        self._narration_id_counter = 0
        self._screen_action_id_counter = 0
        self._narration_open: bool = False
        self._pending_text: str | None = None
        self._pending_narration_id: int = -1
        self._pending_screen_actions: list[ScreenAction] = []
        self._pending_action_id: int | None = None
        self._pending_voice: str | None = None
        self._voices = voices
        self._video_width = video_width
        self._video_height = video_height
        self._current_recorder = None
        self._narration_start_ns: int = 0
        output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def debug_overlay(self) -> bool:
        return self._debug_overlay_flag

    @property
    def font_size(self) -> int:
        return self._font_size_val

    @property
    def highlight_style(self) -> HighlightStyle:
        return self._highlight_style

    def with_highlight_style(self, style: HighlightStyle) -> Storyboard:
        self._highlight_style = _merge_highlight_styles(self._highlight_style, style)
        return self

    def _elapsed_ms(self) -> int:
        return (time.monotonic_ns() - self._narration_start_ns) // 1_000_000

    def _start_recording(self, narration_id: int) -> None:
        from screencast_narrator_client.cdp_video_recorder import CdpVideoRecorder

        video_dir = self._output_dir / "videos"
        video_file = video_dir / f"narration-{narration_id:03d}.mp4"
        self._current_recorder = CdpVideoRecorder(self._page, video_file, self._video_width, self._video_height, self._config)
        self._current_recorder.start()
        self._narration_start_ns = time.monotonic_ns()

    def _stop_recording(self) -> None:
        if self._current_recorder is None:
            return
        self._current_recorder.stop()
        log.info("Narration %d video saved: %s (%d frames)",
                 self._pending_narration_id, self._current_recorder.output_file,
                 self._current_recorder.frame_count)
        self._current_recorder = None

    def begin_narration(self, text: str | None = None, translations: dict[str, str] | None = None, voice: str | None = None) -> int:
        if self._narration_open:
            raise RuntimeError("Cannot begin a new narration while another is still open")
        nid = self._narration_id_counter
        self._narration_id_counter += 1
        self._narration_open = True
        self._pending_narration_id = nid
        self._pending_text = text
        self._pending_voice = voice
        self._pending_translations: dict[str, str] = dict(translations) if translations else {}
        self._pending_screen_actions = []
        if self._page is not None:
            self._start_recording(nid)
        return nid

    def begin_screen_action(
        self,
        type: ScreenActionType = ScreenActionType.navigate,
        description: str | None = None,
        timing: ScreenActionTiming = ScreenActionTiming.casted,
        duration_ms: int | None = None,
    ) -> int:
        if not self._narration_open:
            raise RuntimeError("Cannot begin a screen action outside of a narration bracket")
        if self._pending_action_id is not None:
            raise RuntimeError("Cannot begin a new screen action while another is still open")
        if timing == ScreenActionTiming.timed and duration_ms is None:
            raise ValueError("duration_ms is required when timing is TIMED")
        said = self._screen_action_id_counter
        self._screen_action_id_counter += 1
        timing_value = timing if timing != ScreenActionTiming.casted else None
        self._pending_screen_actions.append(ScreenAction(
            type=type,
            screen_action_id=said,
            description=description,
            timing=timing_value,
            duration_ms=duration_ms,
        ))
        self._pending_action_id = said
        return said

    def highlight(self, locator) -> None:
        if self._page is None:
            raise RuntimeError("Cannot highlight: no page was provided to Storyboard")
        if not self._narration_open:
            raise RuntimeError("Cannot highlight outside of a narration bracket")

        hl_config = self._config.with_highlight_overrides(self._highlight_style)

        said = self._screen_action_id_counter
        self._screen_action_id_counter += 1

        from screencast_narrator_client.highlight import highlight as _highlight

        _highlight(self._page, locator, hl_config)

        self._pending_screen_actions.append(ScreenAction(
            type=ScreenActionType.highlight,
            screen_action_id=said,
        ))

    def end_screen_action(self) -> None:
        if self._pending_action_id is None:
            raise RuntimeError("Cannot end screen action: no screen action is open")
        self._pending_action_id = None

    def end_narration(self) -> None:
        if not self._narration_open:
            raise RuntimeError("Cannot end narration: no narration bracket is open")
        if self._pending_action_id is not None:
            raise RuntimeError("Cannot end narration while a screen action is still open")
        self._stop_recording()
        self._narrations.append(Narration(
            narration_id=self._pending_narration_id,
            text=self._pending_text,
            voice=self._pending_voice,
            screen_actions=list(self._pending_screen_actions) or None,
            translations=dict(self._pending_translations) or None,
            video_file=f"videos/narration-{self._pending_narration_id:03d}.mp4",
        ))
        self._narration_open = False
        self._pending_text = None
        self._pending_voice = None
        self._pending_narration_id = -1
        self._pending_screen_actions = []
        self._flush()

    def narrate(
        self,
        callback: Callable[[Storyboard], None],
        text: str | None = None,
        translations: dict[str, str] | None = None,
        voice: str | None = None,
    ) -> int:
        nid = self.begin_narration(text, translations, voice=voice)
        try:
            callback(self)
        finally:
            if self._pending_action_id is not None:
                self.end_screen_action()
            self.end_narration()
        return nid

    def screen_action(
        self,
        callback: Callable[[Storyboard], None],
        type: ScreenActionType = ScreenActionType.navigate,
        description: str | None = None,
        timing: ScreenActionTiming = ScreenActionTiming.casted,
        duration_ms: int | None = None,
    ) -> int:
        said = self.begin_screen_action(type=type, description=description, timing=timing, duration_ms=duration_ms)
        try:
            callback(self)
        finally:
            self.end_screen_action()
        return said

    def done(self) -> None:
        if self._narration_open:
            raise RuntimeError("Cannot finalize: a narration bracket is still open")
        self._flush()

    @property
    def narrations(self) -> list[Narration]:
        return list(self._narrations)

    def _flush(self) -> None:
        options: Options | None = None
        hl = self._highlight_style if self._highlight_style != HighlightStyle() else None
        if hl or self._voices or self._debug_overlay_flag or self._font_size_val != 24:
            options = Options(
                highlight_style=hl,
                voices=self._voices,
                debug_overlay=True if self._debug_overlay_flag else None,
                font_size=self._font_size_val if self._font_size_val != 24 else None,
            )
        model = StoryboardModel(
            language=self._language,
            narrations=list(self._narrations),
            options=options,
        )
        json_str = model.model_dump_json(indent=2, by_alias=True, exclude_none=True)
        (self._output_dir / "storyboard.json").write_text(json_str, encoding="utf-8")
