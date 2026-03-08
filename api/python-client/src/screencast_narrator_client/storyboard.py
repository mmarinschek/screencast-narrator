"""Storyboard: narration bracket and screen action recording for screencast narration."""

from __future__ import annotations

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
from screencast_narrator_client.shared_config import HighlightConfig, SharedConfig, load_shared_config
from screencast_narrator_client.sync_frames import SyncFrameInjector


def _merge_highlight_styles(base: HighlightStyle, override: HighlightStyle) -> HighlightStyle:
    return HighlightStyle(
        color=override.color if override.color is not None else base.color,
        animation_speed_ms=override.animation_speed_ms if override.animation_speed_ms is not None else base.animation_speed_ms,
        draw_duration_ms=override.draw_duration_ms if override.draw_duration_ms is not None else base.draw_duration_ms,
        opacity=override.opacity if override.opacity is not None else base.opacity,
        padding=override.padding if override.padding is not None else base.padding,
    )


def _apply_highlight_style(style: HighlightStyle, config: HighlightConfig) -> HighlightConfig:
    return HighlightConfig(
        scroll_wait_ms=config.scroll_wait_ms,
        draw_wait_ms=style.draw_duration_ms if style.draw_duration_ms is not None else config.draw_wait_ms,
        remove_wait_ms=config.remove_wait_ms,
        color=style.color if style.color is not None else config.color,
        padding=style.padding if style.padding is not None else config.padding,
        animation_speed_ms=style.animation_speed_ms if style.animation_speed_ms is not None else config.animation_speed_ms,
        line_width_min=config.line_width_min,
        line_width_max=config.line_width_max,
        opacity=style.opacity if style.opacity is not None else config.opacity,
        segments=config.segments,
        coverage=config.coverage,
        scroll_js=config.scroll_js,
        scroll_wait_js=config.scroll_wait_js,
        draw_js=config.draw_js,
        remove_js=config.remove_js,
    )


class Storyboard:
    def __init__(
        self,
        output_dir: Path,
        page=None,
        language: str = "en",
        debug_overlay: bool = False,
        font_size: int = 24,
        highlight_style: HighlightStyle | None = None,
    ) -> None:
        self._output_dir = output_dir
        self._page = page
        self._language = language
        self._debug_overlay = debug_overlay
        self._font_size = font_size
        self._config: SharedConfig = load_shared_config()
        self._sm = self._config.sync_markers
        self._sync = SyncFrameInjector(self._config)
        self._highlight_style = highlight_style or HighlightStyle()
        self._narrations: list[Narration] = []
        self._narration_id_counter = 0
        self._screen_action_id_counter = 0
        self._narration_open: bool = False
        self._pending_text: str | None = None
        self._pending_narration_id: int = -1
        self._pending_screen_actions: list[ScreenAction] = []
        self._pending_action_id: int | None = None
        output_dir.mkdir(parents=True, exist_ok=True)
        self._inject_init_frame()

    @property
    def highlight_style(self) -> HighlightStyle:
        return self._highlight_style

    def with_highlight_style(self, style: HighlightStyle) -> Storyboard:
        self._highlight_style = _merge_highlight_styles(self._highlight_style, style)
        return self

    def begin_narration(self, text: str | None = None, translations: dict[str, str] | None = None) -> int:
        if self._narration_open:
            raise RuntimeError("Cannot begin a new narration while another is still open")
        nid = self._narration_id_counter
        self._narration_id_counter += 1
        self._narration_open = True
        self._pending_narration_id = nid
        self._pending_text = text
        self._pending_translations: dict[str, str] = dict(translations) if translations else {}
        self._pending_screen_actions = []
        if self._page is not None:
            self._sync.inject_sync_frame(self._page, nid, self._sm.start, text, self._pending_translations or None)
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
        timing_str = timing.value if timing != ScreenActionTiming.casted else None
        if self._page is not None:
            self._sync.inject_action_sync_frame(
                self._page, said, self._sm.start, description, type.value, timing_str, duration_ms
            )
        return said

    def highlight(self, locator) -> None:
        if self._page is None:
            raise RuntimeError("Cannot highlight: no page was provided to Storyboard")
        if not self._narration_open:
            raise RuntimeError("Cannot highlight outside of a narration bracket")

        highlight_config = _apply_highlight_style(self._highlight_style, self._config.highlight)

        said = self._screen_action_id_counter
        self._screen_action_id_counter += 1

        self._sync.inject_highlight_sync_frame(self._page, said, self._sm.start)

        from screencast_narrator_client.highlight import highlight as _highlight

        _highlight(self._page, locator, highlight_config)

        self._sync.inject_highlight_sync_frame(self._page, said, self._sm.end)
        self._pending_screen_actions.append(ScreenAction(
            type=ScreenActionType.highlight,
            screen_action_id=said,
        ))

    def end_screen_action(self) -> None:
        if self._pending_action_id is None:
            raise RuntimeError("Cannot end screen action: no screen action is open")
        if self._page is not None:
            self._sync.inject_action_sync_frame(self._page, self._pending_action_id, self._sm.end)
        self._pending_action_id = None

    def end_narration(self) -> None:
        if not self._narration_open:
            raise RuntimeError("Cannot end narration: no narration bracket is open")
        if self._pending_action_id is not None:
            raise RuntimeError("Cannot end narration while a screen action is still open")
        if self._page is not None:
            self._sync.inject_sync_frame(self._page, self._pending_narration_id, self._sm.end)
        self._narrations.append(Narration(
            narration_id=self._pending_narration_id,
            text=self._pending_text,
            screen_actions=list(self._pending_screen_actions) or None,
            translations=dict(self._pending_translations) or None,
        ))
        self._narration_open = False
        self._pending_text = None
        self._pending_narration_id = -1
        self._pending_screen_actions = []
        self._flush()

    @property
    def narrations(self) -> list[Narration]:
        return list(self._narrations)

    def _inject_init_frame(self) -> None:
        if self._page is None:
            return
        self._sync.inject_init_frame(self._page, self._language, self._debug_overlay, self._font_size)

    def _flush(self) -> None:
        options: Options | None = None
        if self._debug_overlay or self._font_size != 24:
            options = Options(
                debug_overlay=self._debug_overlay or None,
                font_size=self._font_size if self._font_size != 24 else None,
            )
        model = StoryboardModel(
            language=self._language,
            narrations=list(self._narrations),
            options=options,
        )
        json_str = model.model_dump_json(indent=2, by_alias=True, exclude_none=True)
        (self._output_dir / "storyboard.json").write_text(json_str, encoding="utf-8")
