"""Main merge pipeline: combines video + TTS audio into a narrated screencast."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from screencast_narrator.ffmpeg import exec_ffmpeg, probe_duration_ms, require_command, secs
from screencast_narrator.freeze_frames import (
    FreezeFrame,
    FreezeFrameCalculator,
    GapCut,
    HighlightEntry,
    NarrationSegment,
    adjust_for_cuts,
    adjust_timestamp,
    detect_dead_air_gaps,
)
from screencast_narrator.sync_detect import (
    SyncDetectionResult,
    SyncFrameSpan,
    build_sync_position_map,
    detect_sync_frames,
    strip_sync_frames,
)
from screencast_narrator.timeline_html import (
    generate_adjusted_html,
    generate_combined_html,
    generate_original_html,
)
from screencast_narrator.tts import KokoroTTS, TTSBackend


@dataclass(frozen=True)
class NarrationText:
    timestamp_ms: int
    end_timestamp_ms: int
    text: str


def process(target_dir: Path, tts_backend: TTSBackend | None = None) -> None:
    timeline_file = target_dir / "timeline.json"
    video_dir = target_dir / "videos"
    audio_dir = target_dir / "narration-audio"
    temp_dir = target_dir / "narration-tmp"
    output_file = target_dir / (target_dir.name + ".mp4")

    if not timeline_file.exists():
        raise RuntimeError(f"Timeline not found at {timeline_file}")
    video_file = _get_video_file(video_dir)
    require_command("ffmpeg")

    audio_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    timeline_root = json.loads(timeline_file.read_text())
    narration_texts = _extract_narrations(timeline_root)
    highlights = _extract_highlights(timeline_root)

    if not narration_texts:
        exec_ffmpeg("-y", "-i", str(video_file),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", str(output_file))
        return

    if tts_backend is None:
        tts_backend = KokoroTTS()
    _generate_tts_audio(narration_texts, audio_dir, tts_backend)

    narrations: list[NarrationSegment] = []
    for i, nt in enumerate(narration_texts):
        audio_duration = probe_duration_ms(audio_dir / _segment_name(i))
        narrations.append(NarrationSegment(nt.timestamp_ms, nt.end_timestamp_ms, nt.text, audio_duration))

    sync_detection = detect_sync_frames(video_file, temp_dir)

    if sync_detection.green_frame_indices:
        _run_sync_frame_pipeline(video_file, sync_detection, narrations, highlights,
                                 timeline_root, audio_dir, temp_dir, output_file)
    else:
        _run_wall_clock_pipeline(video_file, narrations, highlights,
                                 timeline_root, audio_dir, temp_dir, output_file)

    generate_original_html(target_dir)
    generate_adjusted_html(target_dir)
    generate_combined_html(target_dir)


def _segment_name(index: int) -> str:
    return f"segment_{index:03d}.wav"


def _get_video_file(video_dir: Path) -> Path:
    if not video_dir.exists():
        raise RuntimeError(f"Video directory not found: {video_dir}")
    webm_files = sorted(video_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not webm_files:
        raise RuntimeError(f"No .webm file found in {video_dir}")
    return webm_files[-1]


def _get_events(root: dict) -> list[dict]:
    return root.get("events", root if isinstance(root, list) else [])


def _extract_narrations(root: dict) -> list[NarrationText]:
    narrations: list[NarrationText] = []
    for event in _get_events(root):
        if event.get("type") == "narration":
            ts = event["timestampMs"]
            end_ts = event.get("endTimestampMs", ts)
            narrations.append(NarrationText(ts, end_ts, event["text"]))
    return narrations


def _extract_highlights(root: dict) -> list[HighlightEntry]:
    highlights: list[HighlightEntry] = []
    for event in _get_events(root):
        if event.get("type") == "highlight":
            start_ms = event["timestampMs"]
            end_ms = event["endTimestampMs"]
            highlights.append(HighlightEntry(start_ms, end_ms - start_ms))
    return highlights


def _video_recording_offset(root: dict) -> int:
    return root.get("videoRecordingStartedAtMs", 0)


def _compute_video_time_scale(root: dict, video_duration_ms: int) -> float:
    if "videoRecordingStartedAtMs" not in root or "videoRecordingEndedAtMs" not in root:
        return 1.0
    wall_clock_duration_ms = root["videoRecordingEndedAtMs"] - root["videoRecordingStartedAtMs"]
    if wall_clock_duration_ms <= 0:
        return 1.0
    return video_duration_ms / wall_clock_duration_ms


def _generate_tts_audio(narrations: list[NarrationText], audio_dir: Path, tts_backend: TTSBackend) -> None:
    for i, nt in enumerate(narrations):
        wav_file = audio_dir / _segment_name(i)
        if not wav_file.exists():
            tts_backend.generate(nt.text, wav_file)


# --- Sync-frame-based pipeline ---

def _run_sync_frame_pipeline(
    raw_video_file: Path,
    sync_detection: SyncDetectionResult,
    narrations: list[NarrationSegment],
    highlights: list[HighlightEntry],
    timeline_root: dict,
    audio_dir: Path,
    temp_dir: Path,
    output_file: Path,
) -> None:
    qr_spans = sync_detection.qr_spans
    green_frame_indices = sync_detection.green_frame_indices

    sync_positions = build_sync_position_map(qr_spans, green_frame_indices)
    stripped_video = strip_sync_frames(raw_video_file, green_frame_indices, temp_dir)
    stripped_duration_ms = probe_duration_ms(stripped_video)

    stripped_narrations = _to_stripped_video_narrations(
        narrations, sync_positions, qr_spans, green_frame_indices, timeline_root
    )

    video_recording_end_ms = timeline_root.get("videoRecordingEndedAtMs", 2**63 - 1)
    result = FreezeFrameCalculator(stripped_narrations, highlights, video_recording_end_ms).calculate()

    final_video = _build_extended_video_direct(
        stripped_video, result.freeze_frames, stripped_duration_ms / 1000.0, temp_dir
    )

    extended_duration_ms = probe_duration_ms(final_video)
    audio_delays = result.adjusted_timestamps

    max_audio_end_ms = max(
        (audio_delays[i] + stripped_narrations[i].audio_duration_ms for i in range(len(stripped_narrations))),
        default=0,
    )
    tail_freeze_ms = max_audio_end_ms - extended_duration_ms + 5000
    if tail_freeze_ms > 0:
        final_video = _append_tail_freeze(final_video, tail_freeze_ms, temp_dir)

    occupied_intervals: list[tuple[int, int]] = []
    for hl in highlights:
        adj_start = max(0, adjust_timestamp(hl.timestamp_ms, result.freeze_frames))
        adj_end = max(0, adjust_timestamp(hl.timestamp_ms + hl.duration_ms, result.freeze_frames))
        occupied_intervals.append((adj_start, adj_end))

    gap_cuts = detect_dead_air_gaps(stripped_narrations, audio_delays, occupied_intervals)
    if gap_cuts:
        final_video = _cut_gaps(final_video, gap_cuts, temp_dir)
        final_timestamps = [adjust_for_cuts(ts, gap_cuts) for ts in audio_delays]
    else:
        final_timestamps = audio_delays

    _write_gap_cuts_json(gap_cuts, output_file.parent)
    _overlay_audio(final_video, stripped_narrations, final_timestamps, 0, audio_dir, output_file)


def _to_stripped_video_narrations(
    narrations: list[NarrationSegment],
    sync_positions: dict[str, float],
    qr_spans: list[SyncFrameSpan],
    green_frame_indices: set[int],
    timeline_root: dict,
) -> list[NarrationSegment]:
    adjusted: list[NarrationSegment] = []
    for i, n in enumerate(narrations):
        key = f"{i}|START"
        if key in sync_positions:
            sync_start_ms = int(sync_positions[key] * 1000)
            wall_clock_bracket = n.end_ms - n.start_ms
            sync_time_ms = _sync_frame_time_in_bracket_ms(qr_spans, green_frame_indices, i)
            stripped_bracket = max(0, wall_clock_bracket - sync_time_ms)
            adjusted.append(NarrationSegment(
                sync_start_ms, sync_start_ms + stripped_bracket, n.text, n.audio_duration_ms
            ))
        else:
            video_offset = _video_recording_offset(timeline_root)
            adj_start = max(0, n.start_ms - video_offset)
            adj_end = max(0, n.end_ms - video_offset)
            adjusted.append(NarrationSegment(adj_start, adj_end, n.text, n.audio_duration_ms))
    return adjusted


def _sync_frame_time_in_bracket_ms(
    qr_spans: list[SyncFrameSpan], green_frame_indices: set[int], narration_id: int
) -> int:
    green_frames_in_bracket: set[int] = set()
    for span in qr_spans:
        if span.narration_id != narration_id:
            continue
        green_range = _find_green_range_containing(green_frame_indices, span.first_frame)
        for f in range(green_range[0], green_range[1] + 1):
            green_frames_in_bracket.add(f)
    return len(green_frames_in_bracket) * 40


def _find_green_range_containing(green_frame_indices: set[int], frame_index: int) -> tuple[int, int]:
    start = frame_index
    end = frame_index
    while start - 1 in green_frame_indices:
        start -= 1
    while end + 1 in green_frame_indices:
        end += 1
    return (start, end)


# --- Wall-clock-based pipeline ---

def _run_wall_clock_pipeline(
    video_file: Path,
    narrations: list[NarrationSegment],
    highlights: list[HighlightEntry],
    timeline_root: dict,
    audio_dir: Path,
    temp_dir: Path,
    output_file: Path,
) -> None:
    video_duration_ms = probe_duration_ms(video_file)
    video_time_scale = _compute_video_time_scale(timeline_root, video_duration_ms)
    video_offset = _video_recording_offset(timeline_root)

    video_recording_end_ms = timeline_root.get("videoRecordingEndedAtMs", 2**63 - 1)
    result = FreezeFrameCalculator(narrations, highlights, video_recording_end_ms).calculate()

    final_video = _build_extended_video(
        video_file, result.freeze_frames, video_duration_ms / 1000.0,
        video_time_scale, video_offset, temp_dir,
    )

    extended_duration_ms = probe_duration_ms(final_video)

    max_audio_end_ms = max(
        (_audio_delay_ms(result.adjusted_timestamps[i], video_offset) + narrations[i].audio_duration_ms
         for i in range(len(narrations))),
        default=0,
    )
    tail_freeze_ms = max_audio_end_ms - extended_duration_ms + 5000
    if tail_freeze_ms > 0:
        final_video = _append_tail_freeze(final_video, tail_freeze_ms, temp_dir)

    adjusted_for_video = [max(0, ts - video_offset) for ts in result.adjusted_timestamps]

    occupied_intervals: list[tuple[int, int]] = []
    for hl in highlights:
        adj_start = max(0, adjust_timestamp(hl.timestamp_ms, result.freeze_frames) - video_offset)
        adj_end = max(0, adjust_timestamp(hl.timestamp_ms + hl.duration_ms, result.freeze_frames) - video_offset)
        occupied_intervals.append((adj_start, adj_end))
    for event in _get_events(timeline_root):
        if event.get("type") == "action":
            adj_ts = max(0, adjust_timestamp(event["timestampMs"], result.freeze_frames) - video_offset)
            occupied_intervals.append((adj_ts, adj_ts + 500))

    gap_cuts = detect_dead_air_gaps(narrations, adjusted_for_video, occupied_intervals)
    if gap_cuts:
        final_video = _cut_gaps(final_video, gap_cuts, temp_dir)
        final_timestamps = [adjust_for_cuts(ts, gap_cuts) for ts in adjusted_for_video]
    else:
        final_timestamps = adjusted_for_video

    _write_gap_cuts_json(gap_cuts, output_file.parent)
    _overlay_audio(final_video, narrations, final_timestamps, 0, audio_dir, output_file)


# --- Video building ---

def _build_extended_video_direct(
    video_file: Path, freeze_frames: list[FreezeFrame],
    video_duration_s: float, temp_dir: Path,
) -> Path:
    if not freeze_frames:
        return video_file

    sorted_ff = sorted(freeze_frames, key=lambda f: f.time_ms)
    segment_files: list[Path] = []
    last_cut_s = 0.0

    for i, ff in enumerate(sorted_ff):
        cut_s = ff.time_ms / 1000.0
        ff_duration_s = ff.duration_ms / 1000.0

        if cut_s > last_cut_s:
            seg_file = temp_dir / f"sync_seg_{i:03d}.mp4"
            exec_ffmpeg("-y", "-i", str(video_file),
                        "-ss", secs(last_cut_s), "-to", secs(cut_s), "-r", "25",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-an", str(seg_file))
            segment_files.append(seg_file)

        freeze_img = temp_dir / f"sync_freeze_{i:03d}.png"
        exec_ffmpeg("-y", "-i", str(video_file), "-ss", secs(cut_s), "-vframes", "1", str(freeze_img))

        freeze_seg = temp_dir / f"sync_freeze_seg_{i:03d}.mp4"
        exec_ffmpeg("-y", "-r", "25", "-f", "image2", "-i", str(freeze_img),
                    "-vf", "loop=-1:1:0", "-t", secs(ff_duration_s),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-an", str(freeze_seg))
        segment_files.append(freeze_seg)
        last_cut_s = cut_s

    if last_cut_s < video_duration_s - 0.1:
        final_seg = temp_dir / "sync_seg_final.mp4"
        exec_ffmpeg("-y", "-i", str(video_file), "-ss", secs(last_cut_s), "-r", "25",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-an", str(final_seg))
        segment_files.append(final_seg)

    return _concat_segments(segment_files, temp_dir / "sync_concat.txt", temp_dir / "sync_extended.mp4")


def _build_extended_video(
    video_file: Path, freeze_frames: list[FreezeFrame],
    video_duration_s: float, video_time_scale: float,
    video_offset_ms: int, temp_dir: Path,
) -> Path:
    sorted_ff = sorted(freeze_frames, key=lambda f: f.time_ms)
    needs_correction = abs(video_time_scale - 1.0) > 0.02
    itsscale = f"{1.0 / video_time_scale:.6f}"
    timeline_duration_s = video_duration_s / video_time_scale
    effective_duration_s = timeline_duration_s if needs_correction else video_duration_s

    if not sorted_ff:
        if not needs_correction:
            return video_file
        corrected = temp_dir / "corrected.mp4"
        exec_ffmpeg("-y", "-itsscale", itsscale, "-i", str(video_file), "-r", "25",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", str(corrected))
        return corrected

    segment_files: list[Path] = []
    last_cut_video = 0.0

    for i, ff in enumerate(sorted_ff):
        cut_video_s = (ff.time_ms - video_offset_ms) / 1000.0
        ff_duration_s = ff.duration_ms / 1000.0

        if cut_video_s > last_cut_video:
            seg_file = temp_dir / f"seg_{i:03d}.mp4"
            cmd = ["-y"]
            if needs_correction:
                cmd.extend(["-itsscale", itsscale])
            cmd.extend(["-i", str(video_file), "-ss", secs(last_cut_video), "-to", secs(cut_video_s),
                        "-r", "25", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-an", str(seg_file)])
            exec_ffmpeg(*cmd)
            segment_files.append(seg_file)

        freeze_img = temp_dir / f"freeze_{i:03d}.png"
        frame_cmd = ["-y"]
        if needs_correction:
            frame_cmd.extend(["-itsscale", itsscale])
        frame_cmd.extend(["-i", str(video_file), "-ss", secs(cut_video_s), "-vframes", "1", str(freeze_img)])
        exec_ffmpeg(*frame_cmd)

        if not freeze_img.exists():
            raise RuntimeError(
                f"Freeze frame extraction produced no output at seek position {secs(cut_video_s)}s "
                f"(freeze {i} at {ff.time_ms}ms, videoOffset={video_offset_ms}ms, "
                f"effectiveDuration={secs(effective_duration_s)}s). "
                f"The seek position is likely past the end of decodable video frames."
            )

        freeze_seg = temp_dir / f"freeze_seg_{i:03d}.mp4"
        exec_ffmpeg("-y", "-r", "25", "-f", "image2", "-i", str(freeze_img),
                    "-vf", "loop=-1:1:0", "-t", secs(ff_duration_s),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-an", str(freeze_seg))
        segment_files.append(freeze_seg)
        last_cut_video = cut_video_s

    if last_cut_video < effective_duration_s - 0.1:
        final_seg = temp_dir / "seg_final.mp4"
        cmd = ["-y"]
        if needs_correction:
            cmd.extend(["-itsscale", itsscale])
        cmd.extend(["-i", str(video_file), "-ss", secs(last_cut_video), "-r", "25",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-an", str(final_seg)])
        exec_ffmpeg(*cmd)
        segment_files.append(final_seg)

    return _concat_segments(segment_files, temp_dir / "concat.txt", temp_dir / "extended.mp4")


def _concat_segments(segment_files: list[Path], concat_list: Path, output: Path) -> Path:
    content = "\n".join(f"file '{seg.resolve()}'" for seg in segment_files) + "\n"
    concat_list.write_text(content)
    exec_ffmpeg("-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", str(output))
    return output


def _append_tail_freeze(video_file: Path, duration_ms: int, temp_dir: Path) -> Path:
    last_frame = temp_dir / "tail_freeze.png"
    exec_ffmpeg("-y", "-sseof", "-0.1", "-i", str(video_file), "-vframes", "1", str(last_frame))

    freeze_seg = temp_dir / "tail_freeze_seg.mp4"
    exec_ffmpeg("-y", "-r", "25", "-f", "image2", "-i", str(last_frame),
                "-vf", "loop=-1:1:0", "-t", secs(duration_ms / 1000.0),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an", str(freeze_seg))

    concat_list = temp_dir / "tail_concat.txt"
    concat_list.write_text(
        f"file '{video_file.resolve()}'\nfile '{freeze_seg.resolve()}'\n"
    )

    extended = temp_dir / "extended_with_tail.mp4"
    exec_ffmpeg("-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", str(extended))
    return extended


def _cut_gaps(video_file: Path, gap_cuts: list[GapCut], temp_dir: Path) -> Path:
    sorted_gaps = sorted(gap_cuts, key=lambda g: g.start_ms)
    segment_files: list[Path] = []
    last_end_s = 0.0

    for i, gap in enumerate(sorted_gaps):
        cut_start_s = gap.start_ms / 1000.0
        if cut_start_s > last_end_s:
            seg_file = temp_dir / f"kept_{i:03d}.mp4"
            exec_ffmpeg("-y", "-i", str(video_file),
                        "-ss", secs(last_end_s), "-to", secs(cut_start_s),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-an", str(seg_file))
            segment_files.append(seg_file)
        last_end_s = gap.end_ms / 1000.0

    video_duration_s = probe_duration_ms(video_file) / 1000.0
    if last_end_s < video_duration_s - 0.05:
        final_seg = temp_dir / "kept_final.mp4"
        exec_ffmpeg("-y", "-i", str(video_file), "-ss", secs(last_end_s),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-an", str(final_seg))
        segment_files.append(final_seg)

    return _concat_segments(segment_files, temp_dir / "concat_cuts.txt", temp_dir / "cut.mp4")


def _overlay_audio(
    video_file: Path, narrations: list[NarrationSegment],
    adjusted_timestamps: list[int], video_offset_ms: int,
    audio_dir: Path, output_file: Path,
) -> None:
    inputs = ["-i", str(video_file)]
    filter_parts: list[str] = []
    amix_inputs: list[str] = []
    audio_count = 0

    max_audio_end_ms = max(
        (_audio_delay_ms(adjusted_timestamps[i], video_offset_ms) + narrations[i].audio_duration_ms
         for i in range(len(narrations))),
        default=0,
    )
    pad_dur = secs(max_audio_end_ms / 1000.0)

    for i in range(len(narrations)):
        wav_file = audio_dir / _segment_name(i)
        if not wav_file.exists():
            continue
        inputs.extend(["-i", str(wav_file)])
        audio_count += 1
        delay_ms = _audio_delay_ms(adjusted_timestamps[i], video_offset_ms)
        filter_parts.append(f"[{audio_count}:a]adelay={delay_ms}|{delay_ms},apad=whole_dur={pad_dur}[a{i}]")
        amix_inputs.append(f"[a{i}]")

    if not amix_inputs:
        raise RuntimeError(f"No audio segments found in {audio_dir}")

    n = len(amix_inputs)
    mix_filter = "".join(amix_inputs) + f"amix=inputs={n}:duration=longest[amixed];[amixed]volume={n}.0[aout]"
    full_filter = ";".join(filter_parts) + ";" + mix_filter

    cmd = ["-y", *inputs, "-filter_complex", full_filter,
           "-map", "0:v", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-c:a", "aac", "-b:a", "192k", "-shortest", str(output_file)]
    exec_ffmpeg(*cmd)


def _audio_delay_ms(adjusted_timestamp_ms: int, video_offset_ms: int) -> int:
    return max(0, adjusted_timestamp_ms - video_offset_ms)


def _write_gap_cuts_json(gap_cuts: list[GapCut], target_dir: Path) -> None:
    data = [{"startMs": g.start_ms, "endMs": g.end_ms} for g in gap_cuts]
    (target_dir / "gap-cuts.json").write_text(json.dumps(data))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: screencast-narrator <target-dir>", file=sys.stderr)
        sys.exit(1)
    process(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
