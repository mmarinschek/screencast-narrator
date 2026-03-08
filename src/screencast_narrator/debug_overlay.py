"""Debug overlay: generates drawtext filters and text files for pipeline visualization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import qrcode
from PIL import Image

from screencast_narrator.ffmpeg import exec_ffmpeg, secs
from screencast_narrator.freeze_frames import (
    FreezeFrame,
    GapCut,
    NarrationSegment,
    adjust_for_cuts,
    adjust_timestamp,
)
from screencast_narrator.shared_config import load_shared_config
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
    ScreenAction,
    ScreenActionType,
)

_SM = load_shared_config().sync_markers


def _find_font() -> str | None:
    candidates = [
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Supplemental/Courier New.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        Path("C:/Windows/Fonts/consola.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


_FONT_FILE = _find_font()
_BOX = "box=1:boxcolor=black@0.7:boxborderw=6"


@dataclass(frozen=True)
class OverlayResult:
    filter_str: str
    qr_video: Path


def generate_qr_timestamp_video(duration_s: float, temp_dir: Path, qr_size: int = 100) -> Path:
    qr_dir = temp_dir / "qr_timestamps"
    qr_dir.mkdir(exist_ok=True)
    num_frames = int(duration_s) + 2
    for i in range(num_frames):
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(str(i))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((qr_size, qr_size), Image.NEAREST)
        img.save(qr_dir / f"qr_{i:04d}.png")

    qr_video = temp_dir / "qr_timestamps.mp4"
    exec_ffmpeg(
        "-y", "-framerate", "1",
        "-i", str(qr_dir / "qr_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-t", secs(duration_s),
        str(qr_video),
    )
    return qr_video


def generate_overlay_filter(
    narrations: list[NarrationSegment],
    final_timestamps: list[int],
    storyboard: StoryboardModel,
    sync_positions: dict[str, float],
    freeze_frames: list[FreezeFrame],
    gap_cuts: list[GapCut],
    temp_dir: Path,
    font_size: int = 24,
) -> OverlayResult:
    overlay_dir = temp_dir / "overlay_texts"
    overlay_dir.mkdir(exist_ok=True)
    parts: list[str] = []
    idx = 0
    lh = int(font_size * 1.4)

    def _dt_expr(expr: str, x: str, y: int, color: str, enable_range: str = "") -> str:
        font_opt = f":fontfile={_FONT_FILE}" if _FONT_FILE else ""
        enable = f":enable='between(t,{enable_range})'" if enable_range else ""
        return f"drawtext=text='{expr}':x={x}:y={y}:fontsize={font_size}{font_opt}:fontcolor={color}:{_BOX}{enable}"

    def _dt_file(text: str, x: str, y: int, color: str, enable_range: str = "") -> str:
        nonlocal idx
        txt_file = overlay_dir / f"t{idx}.txt"
        txt_file.write_text(text, encoding="utf-8")
        idx += 1
        font_opt = f":fontfile={_FONT_FILE}" if _FONT_FILE else ""
        enable = f":enable='between(t,{enable_range})'" if enable_range else ""
        return f"drawtext=textfile={txt_file}:x={x}:y={y}:fontsize={font_size}{font_opt}:fontcolor={color}:{_BOX}{enable}"

    top = 50
    parts.append(_dt_expr("%{pts\\:hms}", "10", top, "lime"))
    parts.append(_dt_expr("%{pts\\:ms}", "(w-text_w-10)", top, "lime"))

    def _narration_label(i: int) -> str:
        n = narrations[i]
        s = final_timestamps[i]
        e = s + n.audio_duration_ms
        return f"{_fmt_ms(s)}-{_fmt_ms(e)} N{i}: {n.text[:55]}"

    for i, n in enumerate(narrations):
        start_s = final_timestamps[i] / 1000.0
        end_s = (final_timestamps[i] + n.audio_duration_ms) / 1000.0
        rng = f"{start_s:.3f},{end_s:.3f}"
        if i > 0:
            parts.append(_dt_file(f"PREV {_narration_label(i - 1)}", "10", top + 1 * lh, "gray", rng))
        parts.append(_dt_file(f"NOW  {_narration_label(i)}", "10", top + 2 * lh, "white", rng))
        if i < len(narrations) - 1:
            parts.append(_dt_file(f"NEXT {_narration_label(i + 1)}", "10", top + 3 * lh, "gray", rng))

    for narration in storyboard.narrations:
        resolved_actions: list[tuple[ScreenAction, int, int]] = []
        for action in narration.screen_actions or []:
            if action.type == ScreenActionType.highlight:
                start_key = _SM.highlight_start(action.screen_action_id)
                end_key = _SM.highlight_end(action.screen_action_id)
            else:
                start_key = _SM.action_start(action.screen_action_id)
                end_key = _SM.action_end(action.screen_action_id)
            if start_key not in sync_positions or end_key not in sync_positions:
                continue
            s = _to_final_ms(sync_positions[start_key], freeze_frames, gap_cuts)
            e = _to_final_ms(sync_positions[end_key], freeze_frames, gap_cuts)
            if e > s:
                resolved_actions.append((action, s, e))

        for j, (action, start_ms, end_ms) in enumerate(resolved_actions):
            aid = action.screen_action_id
            desc = (action.description or f"Action {aid}")[:50]
            timing_str = action.timing.value if action.timing else "casted"
            rng = f"{start_ms / 1000.0:.3f},{end_ms / 1000.0:.3f}"

            if j > 0:
                prev_a, prev_s, prev_e = resolved_actions[j - 1]
                prev_desc = (prev_a.description or f"Action {prev_a.screen_action_id}")[:45]
                prev_label = f"{_fmt_ms(prev_s)}-{_fmt_ms(prev_e)} A{prev_a.screen_action_id}: {prev_desc}"
                parts.append(_dt_file(f"PREV {prev_label}", "10", top + 5 * lh, "gray", rng))

            time_label = f"{_fmt_ms(start_ms)}-{_fmt_ms(end_ms)}"
            freeze_tag = " [freeze blocked]" if timing_str != "elastic" else ""
            parts.append(_dt_file(f"NOW  {time_label} A{aid}: {desc} [{timing_str}]{freeze_tag}", "10", top + 6 * lh, "cyan", rng))

            if j < len(resolved_actions) - 1:
                next_a, next_s, next_e = resolved_actions[j + 1]
                next_desc = (next_a.description or f"Action {next_a.screen_action_id}")[:45]
                next_label = f"{_fmt_ms(next_s)}-{_fmt_ms(next_e)} A{next_a.screen_action_id}: {next_desc}"
                parts.append(_dt_file(f"NEXT {next_label}", "10", top + 7 * lh, "gray", rng))

    resolved_ffs: list[tuple[int, int, int]] = []
    for ff in sorted(freeze_frames, key=lambda f: f.time_ms):
        ff_start_extended = adjust_timestamp(ff.time_ms, freeze_frames)
        ff_end_extended = ff_start_extended + ff.duration_ms
        ff_start_final = adjust_for_cuts(ff_start_extended, gap_cuts)
        ff_end_final = adjust_for_cuts(ff_end_extended, gap_cuts)
        if ff_end_final > ff_start_final:
            resolved_ffs.append((ff_start_final, ff_end_final, ff.duration_ms))

    def _ff_label(s: int, e: int, dur: int) -> str:
        return f"{_fmt_ms(s)}-{_fmt_ms(e)} FREEZE ({dur}ms)"

    for k, (ff_s, ff_e, ff_dur) in enumerate(resolved_ffs):
        rng = f"{ff_s / 1000.0:.3f},{ff_e / 1000.0:.3f}"
        if k > 0:
            ps, pe, pd = resolved_ffs[k - 1]
            parts.append(_dt_file(f"PREV {_ff_label(ps, pe, pd)}", "10", top + 9 * lh, "gray", rng))
        parts.append(_dt_file(f"NOW  {_ff_label(ff_s, ff_e, ff_dur)}", "10", top + 10 * lh, "magenta", rng))
        if k < len(resolved_ffs) - 1:
            ns, ne, nd = resolved_ffs[k + 1]
            parts.append(_dt_file(f"NEXT {_ff_label(ns, ne, nd)}", "10", top + 11 * lh, "gray", rng))

    max_end_ms = max(
        (final_timestamps[i] + narrations[i].audio_duration_ms for i in range(len(narrations))),
        default=0,
    )
    duration_s = max_end_ms / 1000.0 + 2.0
    qr_video = generate_qr_timestamp_video(duration_s, temp_dir)

    return OverlayResult(filter_str=",".join(parts), qr_video=qr_video)


def _fmt_ms(ms: int) -> str:
    total_s = ms / 1000.0
    minutes = int(total_s) // 60
    seconds = total_s - minutes * 60
    return f"{minutes:02d}:{seconds:06.3f}"


def _to_final_ms(pos_s: float, freeze_frames: list[FreezeFrame], gap_cuts: list[GapCut]) -> int:
    ms = int(pos_s * 1000)
    ms = adjust_timestamp(ms, freeze_frames)
    return adjust_for_cuts(ms, gap_cuts)
