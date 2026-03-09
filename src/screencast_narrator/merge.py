"""Main merge pipeline: combines video + TTS audio into a narrated screencast."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

from screencast_narrator.ffmpeg import exec_ffmpeg, probe_duration_ms, require_command, secs
from screencast_narrator.freeze_frames import (
    FreezeFrame,
    FreezeFrameCalculator,
    GapCut,
    HighlightEntry,
    NarrationSegment,
    adjust_for_cuts,
    detect_dead_air_gaps,
)
from screencast_narrator.sync_detect import (
    SyncDetectionResult,
    build_sync_position_map,
    detect_sync_frames,
    strip_sync_frames,
)
from screencast_narrator.debug_overlay import OverlayResult, generate_overlay_filter
from screencast_narrator.shared_config import load_shared_config
from screencast_narrator.timeline_html import generate_timeline_html
from screencast_narrator.tts import KokoroTTS, TTSBackend
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
    Narration as StoryboardNarration,
    Options as StoryboardOptions,
    ScreenAction,
    ScreenActionTiming,
    ScreenActionType,
)

_SM = load_shared_config().sync_markers


def process(
    target_dir: Path,
    tts_backend: TTSBackend | None = None,
    debug_overlay: bool | None = None,
    font_size: int | None = None,
) -> None:
    video_dir = target_dir / "videos"
    audio_dir = target_dir / "narration-audio"
    temp_dir = target_dir / "narration-tmp"
    output_file = target_dir / (target_dir.name + ".mp4")

    video_file = _get_video_file(video_dir)
    require_command("ffmpeg")

    temp_dir.mkdir(parents=True, exist_ok=True)

    sync_detection = detect_sync_frames(video_file, temp_dir)
    if not sync_detection.green_frame_indices:
        raise RuntimeError(
            "No sync frames detected in video. Inject sync frames during recording using inject_sync_frame()."
        )

    storyboard = _build_storyboard_from_sync(sync_detection)

    init_data = sync_detection.init_data
    if debug_overlay is None:
        debug_overlay = init_data.get("debugOverlay", False)
    if font_size is None:
        font_size = init_data.get("fontSize", 24)

    narration_texts = _extract_narration_texts(storyboard)

    if not narration_texts:
        narration_spans = [s for s in sync_detection.qr_spans if s.sync_type == _SM.narration]
        if narration_spans:
            raise RuntimeError(
                f"Detected {len(narration_spans)} narration sync frames but extracted 0 narration texts. "
                f"This likely means the marker values in the recording client don't match the shared config."
            )
        exec_ffmpeg("-y", "-i", str(video_file), "-c:v", "libx264", "-preset", "fast", "-crf", "23", str(output_file))
        return

    audio_dir.mkdir(parents=True, exist_ok=True)

    if tts_backend is None:
        tts_backend = KokoroTTS()
    _generate_tts_audio(storyboard, audio_dir, tts_backend)

    audio_durations: list[int] = []
    for i in range(len(narration_texts)):
        wav_file = audio_dir / _segment_name(i)
        audio_durations.append(probe_duration_ms(wav_file) if wav_file.exists() else 0)

    _run_sync_frame_pipeline(
        video_file, sync_detection, storyboard, audio_durations, audio_dir, temp_dir, output_file,
        debug_overlay, font_size,
    )

    generate_timeline_html(target_dir)


def _build_storyboard_from_sync(sync_detection: SyncDetectionResult) -> StoryboardModel:
    sorted_spans = sorted(sync_detection.qr_spans, key=lambda s: s.first_frame)

    narration_screen_action_ids: dict[int, list[int]] = {}
    current_narration_id: int | None = None

    for span in sorted_spans:
        if span.sync_type == _SM.narration:
            if span.marker == _SM.start:
                current_narration_id = span.entity_id
                narration_screen_action_ids.setdefault(current_narration_id, [])
            elif span.marker == _SM.end:
                current_narration_id = None
        elif span.marker == _SM.start and current_narration_id is not None and span.sync_type in (_SM.action, _SM.highlight):
            narration_screen_action_ids[current_narration_id].append(span.entity_id)

    all_narration_ids = set(sync_detection.narration_texts.keys()) | set(narration_screen_action_ids.keys())

    narrations: list[StoryboardNarration] = []
    for narration_id in sorted(all_narration_ids):
        text = sync_detection.narration_texts.get(narration_id)
        translations = sync_detection.narration_translations.get(narration_id)
        action_ids = narration_screen_action_ids.get(narration_id, [])
        screen_actions: list[ScreenAction] = []
        for aid in action_ids:
            detected = sync_detection.screen_actions.get(aid)
            if detected:
                screen_actions.append(detected)
            else:
                screen_actions.append(ScreenAction(
                    type=ScreenActionType.navigate,
                    screen_action_id=aid,
                ))

        voice = sync_detection.narration_voices.get(narration_id)
        narrations.append(StoryboardNarration(
            narration_id=narration_id,
            text=text,
            voice=voice,
            translations=translations,
            screen_actions=screen_actions or None,
        ))

    language = sync_detection.init_data.get("language", "en")
    voices_map = sync_detection.init_data.get("voices")
    options = StoryboardOptions(voices=voices_map) if voices_map else None
    return StoryboardModel(language=language, narrations=narrations, options=options)


def _segment_name(index: int) -> str:
    return f"segment_{index:03d}.wav"


def _get_video_file(video_dir: Path) -> Path:
    if not video_dir.exists():
        raise RuntimeError(f"Video directory not found: {video_dir}")
    webm_files = sorted(video_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not webm_files:
        raise RuntimeError(f"No .webm file found in {video_dir}")
    return webm_files[-1]


def _extract_narration_texts(storyboard: StoryboardModel) -> list[str]:
    return [n.text or "" for n in storyboard.narrations]


def _resolve_voice(
    storyboard: StoryboardModel,
    narration: StoryboardNarration,
) -> str | None:
    voices = storyboard.options.voices if storyboard.options and storyboard.options.voices else {}
    if not voices:
        return None
    alias = narration.voice
    if alias is None:
        first_alias = next(iter(voices), None)
        if first_alias is None:
            return None
        alias = first_alias
    voice_map = voices.get(alias)
    if voice_map is None:
        return None
    return voice_map.get(storyboard.language)


def _generate_tts_audio(storyboard: StoryboardModel, audio_dir: Path, tts_backend: TTSBackend) -> None:
    for i, narration in enumerate(storyboard.narrations):
        text = narration.text or ""
        if not text:
            continue
        wav_file = audio_dir / _segment_name(i)
        if not wav_file.exists():
            voice = _resolve_voice(storyboard, narration)
            tts_backend.generate(text, wav_file, voice=voice)


class IncompleteSyncError(RuntimeError):
    def __init__(self, message: str, narrations: list[NarrationSegment]):
        super().__init__(message)
        self.narrations = narrations


def _build_narrations_from_sync(
    storyboard: StoryboardModel,
    narration_texts: list[str],
    audio_durations: list[int],
    sync_positions: dict[str, float],
) -> list[NarrationSegment]:
    narrations: list[NarrationSegment] = []
    for i, text in enumerate(narration_texts):
        start_key = _SM.narration_start(i)
        end_key = _SM.narration_end(i)
        if start_key not in sync_positions:
            raise IncompleteSyncError(
                f"Missing START sync frame for narration {i}", narrations
            )
        if end_key not in sync_positions:
            end_key = _find_last_action_end_key(storyboard, i, sync_positions)
            if end_key is None:
                raise IncompleteSyncError(
                    f"Missing END sync frame for narration {i}", narrations
                )
        start_ms = int(sync_positions[start_key] * 1000)
        end_ms = int(sync_positions[end_key] * 1000)
        narrations.append(NarrationSegment(start_ms, end_ms, text, audio_durations[i]))
    return narrations


def _find_last_action_end_key(
    storyboard: StoryboardModel, narration_index: int, sync_positions: dict[str, float]
) -> str | None:
    if narration_index >= len(storyboard.narrations):
        return None
    actions = storyboard.narrations[narration_index].screen_actions or []
    for action in reversed(actions):
        if action.type == ScreenActionType.highlight:
            key = _SM.highlight_end(action.screen_action_id)
        else:
            key = _SM.action_end(action.screen_action_id)
        if key in sync_positions:
            return key
    return None


def _build_highlights(
    storyboard: StoryboardModel,
    sync_positions: dict[str, float],
) -> list[HighlightEntry]:
    highlights: list[HighlightEntry] = []
    for narration in storyboard.narrations:
        for action in narration.screen_actions or []:
            if action.timing == ScreenActionTiming.elastic:
                continue
            if action.type == ScreenActionType.highlight:
                start_key = _SM.highlight_start(action.screen_action_id)
                end_key = _SM.highlight_end(action.screen_action_id)
            else:
                start_key = _SM.action_start(action.screen_action_id)
                end_key = _SM.action_end(action.screen_action_id)
            if start_key not in sync_positions or end_key not in sync_positions:
                continue
            start_ms = int(sync_positions[start_key] * 1000)
            end_ms = int(sync_positions[end_key] * 1000)
            if end_ms > start_ms:
                highlights.append(HighlightEntry(start_ms, end_ms - start_ms))
    return highlights


def _run_sync_frame_pipeline(
    raw_video_file: Path,
    sync_detection: SyncDetectionResult,
    storyboard: StoryboardModel,
    audio_durations: list[int],
    audio_dir: Path,
    temp_dir: Path,
    output_file: Path,
    debug_overlay: bool = False,
    font_size: int = 24,
) -> None:
    narration_texts = _extract_narration_texts(storyboard)
    qr_spans = sync_detection.qr_spans
    green_frame_indices = sync_detection.green_frame_indices

    sync_positions = build_sync_position_map(qr_spans, green_frame_indices)
    stripped_video = strip_sync_frames(raw_video_file, green_frame_indices, temp_dir)
    stripped_duration_ms = probe_duration_ms(stripped_video)

    try:
        narrations = _build_narrations_from_sync(storyboard, narration_texts, audio_durations, sync_positions)
    except IncompleteSyncError as exc:
        target_dir = output_file.parent
        _write_partial_diagnostics(
            storyboard, exc.narrations, sync_positions, target_dir
        )
        generate_timeline_html(target_dir)
        raise

    highlights = _build_highlights(storyboard, sync_positions)

    result = FreezeFrameCalculator(narrations, highlights, stripped_duration_ms).calculate()

    final_video = _build_extended_video(stripped_video, result.freeze_frames, stripped_duration_ms / 1000.0, temp_dir)

    extended_duration_ms = probe_duration_ms(final_video)
    audio_delays = result.adjusted_timestamps

    max_audio_end_ms = max(
        (audio_delays[i] + narrations[i].audio_duration_ms for i in range(len(narrations))),
        default=0,
    )
    tail_freeze_ms = max_audio_end_ms - extended_duration_ms
    if tail_freeze_ms > 0:
        final_video = _append_tail_freeze(final_video, tail_freeze_ms, temp_dir)

    gap_cuts = detect_dead_air_gaps(narrations, audio_delays, [])
    if gap_cuts:
        final_video = _cut_gaps(final_video, gap_cuts, temp_dir)
        final_timestamps = [adjust_for_cuts(ts, gap_cuts) for ts in audio_delays]
    else:
        final_timestamps = audio_delays

    _write_gap_cuts_json(gap_cuts, output_file.parent)
    _write_timeline(
        storyboard, narrations, result.adjusted_timestamps, result.freeze_frames, gap_cuts, output_file.parent
    )

    overlay: OverlayResult | None = None
    if debug_overlay:
        overlay = generate_overlay_filter(
            narrations, final_timestamps, storyboard, sync_positions,
            result.freeze_frames, gap_cuts, temp_dir, font_size,
        )

    primary_srt = output_file.with_suffix(".srt")
    _write_srt(narrations, final_timestamps, primary_srt)
    srt_files: list[tuple[Path, str]] = [(primary_srt, storyboard.language)]

    translation_langs: set[str] = set()
    for sn in storyboard.narrations:
        if sn.translations:
            translation_langs.update(sn.translations.keys())

    for lang in sorted(translation_langs):
        lang_srt = output_file.with_name(f"{output_file.stem}_{lang}.srt")
        _write_srt(narrations, final_timestamps, lang_srt, storyboard.narrations, lang)
        srt_files.append((lang_srt, lang))

    _overlay_audio(final_video, narrations, final_timestamps, audio_dir, output_file, overlay, srt_files)


# --- Video building ---


def _extract_freeze_pngs(
    video_file: Path,
    sorted_ff: list[FreezeFrame],
    video_duration_s: float,
    temp_dir: Path,
) -> None:
    frame_times: list[tuple[int, float]] = []
    for i, ff in enumerate(sorted_ff):
        extract_s = min(ff.time_ms / 1000.0, max(video_duration_s - 0.04, 0.0))
        frame_times.append((i, extract_s))

    frame_nums = [round(t * 25) for _, t in frame_times]
    select_expr = "+".join(f"eq(n,{n})" for n in frame_nums)

    freeze_dir = temp_dir / "freeze_pngs"
    freeze_dir.mkdir(exist_ok=True)

    filter_file = temp_dir / "freeze_select.txt"
    filter_file.write_text(f"select='{select_expr}',setpts=N/TB", encoding="utf-8")

    exec_ffmpeg(
        "-y", "-i", str(video_file),
        "-filter_script:v", str(filter_file),
        "-vsync", "vfr",
        str(freeze_dir / "f_%04d.png"),
    )

    extracted = sorted(freeze_dir.glob("f_*.png"))
    for idx, (i, _) in enumerate(frame_times):
        target = temp_dir / f"freeze_{i:03d}.png"
        if idx < len(extracted):
            extracted[idx].rename(target)
        else:
            exec_ffmpeg(
                "-y", "-i", str(video_file),
                "-ss", secs(frame_times[i][1]),
                "-vframes", "1",
                str(target),
            )


def _build_extended_video(
    video_file: Path,
    freeze_frames: list[FreezeFrame],
    video_duration_s: float,
    temp_dir: Path,
) -> Path:
    if not freeze_frames:
        return video_file

    sorted_ff = sorted(freeze_frames, key=lambda f: f.time_ms)

    _extract_freeze_pngs(video_file, sorted_ff, video_duration_s, temp_dir)

    segment_files: list[Path] = []
    last_cut_s = 0.0

    for i, ff in enumerate(sorted_ff):
        cut_s = ff.time_ms / 1000.0
        ff_duration_s = ff.duration_ms / 1000.0

        if cut_s > last_cut_s:
            seg_file = temp_dir / f"seg_{i:03d}.mp4"
            exec_ffmpeg(
                "-y",
                "-i",
                str(video_file),
                "-ss",
                secs(last_cut_s),
                "-to",
                secs(cut_s),
                "-r",
                "25",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-an",
                str(seg_file),
            )
            segment_files.append(seg_file)

        freeze_img = temp_dir / f"freeze_{i:03d}.png"
        freeze_seg = temp_dir / f"freeze_seg_{i:03d}.mp4"
        exec_ffmpeg(
            "-y",
            "-r",
            "25",
            "-f",
            "image2",
            "-i",
            str(freeze_img),
            "-vf",
            "loop=-1:1:0",
            "-t",
            secs(ff_duration_s),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(freeze_seg),
        )
        segment_files.append(freeze_seg)
        last_cut_s = cut_s

    if last_cut_s < video_duration_s - 0.1:
        final_seg = temp_dir / "seg_final.mp4"
        exec_ffmpeg(
            "-y",
            "-i",
            str(video_file),
            "-ss",
            secs(last_cut_s),
            "-r",
            "25",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-an",
            str(final_seg),
        )
        segment_files.append(final_seg)

    return _concat_segments(segment_files, temp_dir / "concat.txt", temp_dir / "extended.mp4")


def _concat_segments(segment_files: list[Path], concat_list: Path, output: Path) -> Path:
    content = "\n".join(f"file '{seg.resolve()}'" for seg in segment_files) + "\n"
    concat_list.write_text(content, encoding="utf-8")
    exec_ffmpeg(
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-an",
        str(output),
    )
    return output


def _append_tail_freeze(video_file: Path, duration_ms: int, temp_dir: Path) -> Path:
    last_frame = temp_dir / "tail_freeze.png"
    exec_ffmpeg("-y", "-sseof", "-0.1", "-i", str(video_file), "-vframes", "1", str(last_frame))

    freeze_seg = temp_dir / "tail_freeze_seg.mp4"
    exec_ffmpeg(
        "-y",
        "-r",
        "25",
        "-f",
        "image2",
        "-i",
        str(last_frame),
        "-vf",
        "loop=-1:1:0",
        "-t",
        secs(duration_ms / 1000.0),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(freeze_seg),
    )

    concat_list = temp_dir / "tail_concat.txt"
    concat_list.write_text(f"file '{video_file.resolve()}'\nfile '{freeze_seg.resolve()}'\n", encoding="utf-8")

    extended = temp_dir / "extended_with_tail.mp4"
    exec_ffmpeg(
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-an",
        str(extended),
    )
    return extended


def _cut_gaps(video_file: Path, gap_cuts: list[GapCut], temp_dir: Path) -> Path:
    sorted_gaps = sorted(gap_cuts, key=lambda g: g.start_ms)
    segment_files: list[Path] = []
    last_end_s = 0.0

    for i, gap in enumerate(sorted_gaps):
        cut_start_s = gap.start_ms / 1000.0
        if cut_start_s > last_end_s:
            seg_file = temp_dir / f"kept_{i:03d}.mp4"
            exec_ffmpeg(
                "-y",
                "-i",
                str(video_file),
                "-ss",
                secs(last_end_s),
                "-to",
                secs(cut_start_s),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-an",
                str(seg_file),
            )
            segment_files.append(seg_file)
        last_end_s = gap.end_ms / 1000.0

    video_duration_s = probe_duration_ms(video_file) / 1000.0
    if last_end_s < video_duration_s - 0.05:
        final_seg = temp_dir / "kept_final.mp4"
        exec_ffmpeg(
            "-y",
            "-i",
            str(video_file),
            "-ss",
            secs(last_end_s),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-an",
            str(final_seg),
        )
        segment_files.append(final_seg)

    return _concat_segments(segment_files, temp_dir / "concat_cuts.txt", temp_dir / "cut.mp4")


def _fmt_srt_time(ms: int) -> str:
    ms = max(0, ms)
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    mi = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{mi:03d}"


def _write_srt(
    narrations: list[NarrationSegment],
    adjusted_timestamps: list[int],
    srt_file: Path,
    storyboard_narrations: list[StoryboardNarration] | None = None,
    language: str | None = None,
) -> None:
    lines: list[str] = []
    seq = 0
    for i, narration in enumerate(narrations):
        if language is not None and storyboard_narrations is not None:
            translations = storyboard_narrations[i].translations or {}
            text = translations.get(language)
            if not text:
                continue
        else:
            text = narration.text
        if not text:
            continue
        seq += 1
        start = adjusted_timestamps[i]
        end = start + narration.audio_duration_ms
        lines.append(str(seq))
        lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
        lines.append(text)
        lines.append("")
    srt_file.write_text("\n".join(lines), encoding="utf-8")


_LANG_TO_ISO639 = {
    "en": "eng", "de": "deu", "fr": "fra", "es": "spa", "it": "ita",
    "pt": "por", "nl": "nld", "pl": "pol", "cs": "ces", "ja": "jpn",
    "zh": "zho", "ko": "kor", "ru": "rus", "ar": "ara", "hi": "hin",
}


_AUDIO_BATCH_SIZE = 50


def _mix_audio_batch(
    wav_entries: list[tuple[Path, int]],
    pad_dur: str,
    output_wav: Path,
) -> None:
    n = len(wav_entries)
    filter_file = output_wav.parent / f"audio_filter_{output_wav.stem}.txt"

    filter_parts = []
    amix_labels = []
    for idx, (_, delay_ms) in enumerate(wav_entries):
        filter_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},apad=whole_dur={pad_dur}[a{idx}]")
        amix_labels.append(f"[a{idx}]")

    mix_filter = ";".join(filter_parts) + ";" + "".join(amix_labels) + f"amix=inputs={n}:duration=longest[amixed];[amixed]volume={n}.0[aout]"
    filter_file.write_text(mix_filter, encoding="utf-8")

    inputs: list[str] = []
    for wav, _ in wav_entries:
        inputs.extend(["-i", str(wav)])

    exec_ffmpeg("-y", *inputs, "-filter_complex_script", str(filter_file), "-map", "[aout]", str(output_wav))


def _premix_audio(
    narrations: list[NarrationSegment],
    adjusted_timestamps: list[int],
    audio_dir: Path,
    mixed_wav: Path,
) -> bool:
    wav_entries: list[tuple[Path, int]] = []
    for i in range(len(narrations)):
        wav_file = audio_dir / _segment_name(i)
        if not wav_file.exists():
            continue
        delay_ms = max(0, adjusted_timestamps[i])
        wav_entries.append((wav_file, delay_ms))

    if not wav_entries:
        return False

    max_audio_end_ms = max(
        max(0, adjusted_timestamps[i]) + narrations[i].audio_duration_ms
        for i in range(len(narrations))
    )
    pad_dur = secs(max_audio_end_ms / 1000.0)

    if len(wav_entries) <= _AUDIO_BATCH_SIZE:
        _mix_audio_batch(wav_entries, pad_dur, mixed_wav)
        return True

    batch_wavs: list[Path] = []
    for batch_idx in range(0, len(wav_entries), _AUDIO_BATCH_SIZE):
        batch = wav_entries[batch_idx:batch_idx + _AUDIO_BATCH_SIZE]
        batch_wav = mixed_wav.parent / f"audio_batch_{batch_idx}.wav"
        _mix_audio_batch(batch, pad_dur, batch_wav)
        batch_wavs.append(batch_wav)

    final_entries = [(bw, 0) for bw in batch_wavs]
    _mix_audio_batch(final_entries, pad_dur, mixed_wav)
    return True


def _overlay_audio(
    video_file: Path,
    narrations: list[NarrationSegment],
    adjusted_timestamps: list[int],
    audio_dir: Path,
    output_file: Path,
    overlay: OverlayResult | None = None,
    srt_files: list[tuple[Path, str]] | None = None,
) -> None:
    temp_dir = output_file.parent
    mixed_wav = temp_dir / "premixed_audio.wav"
    has_audio = _premix_audio(narrations, adjusted_timestamps, audio_dir, mixed_wav)

    max_audio_end_ms = max(
        (max(0, adjusted_timestamps[i]) + narrations[i].audio_duration_ms for i in range(len(narrations))),
        default=0,
    )

    inputs = ["-i", str(video_file)]
    next_input_idx = 1

    qr_input_idx: int | None = None
    if overlay is not None:
        inputs.extend(["-i", str(overlay.qr_video)])
        qr_input_idx = next_input_idx
        next_input_idx += 1

    audio_input_idx: int | None = None
    if has_audio:
        inputs.extend(["-i", str(mixed_wav)])
        audio_input_idx = next_input_idx
        next_input_idx += 1

    if overlay is not None and qr_input_idx is not None:
        video_filter = f"[0:v]{overlay.filter_str}[_vtmp];[_vtmp][{qr_input_idx}:v]overlay=x=W-w-10:y=H-h-10[vout]"
        video_map = "[vout]"
    else:
        video_filter = None
        video_map = "0:v"

    srt_input_indices: list[tuple[int, str]] = []
    if srt_files:
        for i, (srt_path, lang) in enumerate(srt_files):
            if srt_path.stat().st_size == 0 or not srt_path.read_text(encoding="utf-8").strip():
                continue
            srt_idx = next_input_idx
            next_input_idx += 1
            inputs.extend(["-i", str(srt_path)])
            srt_input_indices.append((srt_idx, lang))

    cmd = ["-y", *inputs]
    if video_filter is not None:
        filter_script = temp_dir / "filter_complex.txt"
        filter_script.write_text(video_filter, encoding="utf-8")
        cmd.extend(["-filter_complex_script", str(filter_script)])
        cmd.extend(["-map", video_map])
    else:
        cmd.extend(["-map", video_map])
    if has_audio and audio_input_idx is not None:
        cmd.extend(["-map", f"{audio_input_idx}:a"])
    for srt_idx, _ in srt_input_indices:
        cmd.extend(["-map", str(srt_idx)])
    cmd.extend([
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
    ])
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    if srt_input_indices:
        cmd.extend(["-c:s", "mov_text"])
        for i, (_, lang) in enumerate(srt_input_indices):
            iso = _LANG_TO_ISO639.get(lang, lang)
            cmd.extend([f"-metadata:s:s:{i}", f"language={iso}"])
    video_duration_ms = probe_duration_ms(video_file)
    output_duration_ms = max(video_duration_ms, max_audio_end_ms)
    cmd.extend(["-t", secs(output_duration_ms / 1000.0), str(output_file)])
    exec_ffmpeg(*cmd)


def _write_partial_diagnostics(
    storyboard: StoryboardModel,
    narrations: list[NarrationSegment],
    sync_positions: dict[str, float],
    target_dir: Path,
) -> None:
    timestamps = [n.start_ms for n in narrations]
    _write_timeline(storyboard, narrations, timestamps, [], [], target_dir)

    storyboard_data: dict = {
        "language": storyboard.language,
        "narrations": [
            {
                "narrationId": n.narration_id,
                "text": n.text,
                **({"voice": n.voice} if n.voice else {}),
                **({"translations": n.translations} if n.translations else {}),
                **({"screenActions": [_screen_action_to_json(a) for a in n.screen_actions]} if n.screen_actions else {}),
            }
            for n in storyboard.narrations
        ],
    }
    if storyboard.options and storyboard.options.voices:
        storyboard_data["options"] = {"voices": storyboard.options.voices}
    (target_dir / "storyboard.json").write_text(
        json.dumps(storyboard_data, indent=2), encoding="utf-8"
    )

    sorted_positions = dict(sorted(sync_positions.items(), key=lambda kv: kv[1]))
    (target_dir / "sync_positions.json").write_text(
        json.dumps(sorted_positions, indent=2), encoding="utf-8"
    )


def _write_gap_cuts_json(gap_cuts: list[GapCut], target_dir: Path) -> None:
    data = [{"startMs": g.start_ms, "endMs": g.end_ms} for g in gap_cuts]
    (target_dir / "gap-cuts.json").write_text(json.dumps(data), encoding="utf-8")


def _screen_action_to_json(action: ScreenAction) -> dict:
    result: dict = {"type": action.type.value, "screenActionId": action.screen_action_id}
    if action.description is not None:
        result["description"] = action.description
    if action.timing is not None and action.timing != ScreenActionTiming.casted:
        result["timing"] = action.timing.value
    if action.duration_ms is not None:
        result["durationMs"] = action.duration_ms
    return result


def _write_timeline(
    storyboard: StoryboardModel,
    narrations: list[NarrationSegment],
    adjusted_timestamps: list[int],
    freeze_frames: list[FreezeFrame],
    gap_cuts: list[GapCut],
    target_dir: Path,
) -> None:
    timeline_narrations = []
    for i, n in enumerate(narrations):
        entry: dict = {
            "narrationId": i,
            "text": n.text,
            "timestampMs": adjusted_timestamps[i],
            "endTimestampMs": adjusted_timestamps[i] + n.audio_duration_ms,
            "audioDurationMs": n.audio_duration_ms,
            "bracketStartMs": n.start_ms,
            "bracketEndMs": n.end_ms,
        }
        if i < len(storyboard.narrations) and storyboard.narrations[i].screen_actions:
            entry["screenActions"] = [_screen_action_to_json(a) for a in storyboard.narrations[i].screen_actions]
        timeline_narrations.append(entry)

    data = {
        "narrations": timeline_narrations,
        "freezeFrames": [{"timeMs": ff.time_ms, "durationMs": ff.duration_ms} for ff in freeze_frames],
        "gapCuts": [{"startMs": gc.start_ms, "endMs": gc.end_ms} for gc in gap_cuts],
    }
    (target_dir / "timeline.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: screencast-narrator [--debug-overlay] [--font-size N] <target-dir>",
            file=sys.stderr,
        )
        sys.exit(1)
    args = sys.argv[1:]
    debug_overlay = "--debug-overlay" in args
    args = [a for a in args if a != "--debug-overlay"]
    font_size: int | None = None
    if "--font-size" in args:
        idx = args.index("--font-size")
        font_size = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    process(Path(args[0]), debug_overlay=debug_overlay, font_size=font_size)


if __name__ == "__main__":
    main()
