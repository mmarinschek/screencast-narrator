"""Main merge pipeline: combines per-narration videos + TTS audio into a narrated screencast."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

from screencast_narrator.ffmpeg import exec_ffmpeg, probe_duration_ms, require_command, secs
from screencast_narrator.narration_segment import NarrationSegment
from screencast_narrator.debug_overlay import OverlayResult, generate_overlay_filter
from screencast_narrator.timeline_html import generate_timeline_html
from screencast_narrator.tts import KokoroTTS, TTSBackend
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
    Narration as StoryboardNarration,
    Options as StoryboardOptions,
)


def process(
    target_dir: Path,
    tts_backend: TTSBackend | None = None,
    debug_overlay: bool | None = None,
    font_size: int | None = None,
) -> None:
    storyboard_file = target_dir / "storyboard.json"
    if not storyboard_file.exists():
        raise RuntimeError(f"storyboard.json not found in {target_dir}")

    storyboard_data = json.loads(storyboard_file.read_text(encoding="utf-8"))
    narrations = storyboard_data.get("narrations", [])
    if not narrations or "videoFile" not in narrations[0]:
        raise RuntimeError(
            "Per-narration video files expected. Each narration must have a 'videoFile' entry. "
            "Use CdpVideoRecorder to record per-narration videos during browser automation."
        )

    _process_per_narration_videos(
        target_dir, storyboard_data, tts_backend, debug_overlay, font_size
    )


def _process_per_narration_videos(
    target_dir: Path,
    storyboard_data: dict,
    tts_backend: TTSBackend | None = None,
    debug_overlay: bool | None = None,
    font_size: int | None = None,
) -> None:
    audio_dir = target_dir / "narration-audio"
    temp_dir = target_dir / "narration-tmp"
    output_file = target_dir / (target_dir.name + ".mp4")

    require_command("ffmpeg")
    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    options = storyboard_data.get("options", {})
    if debug_overlay is None:
        debug_overlay = options.get("debugOverlay", False)
    if font_size is None:
        font_size = options.get("fontSize", 24)

    language = storyboard_data.get("language", "en")
    narration_entries = storyboard_data.get("narrations", [])
    voices_map = options.get("voices")

    storyboard = StoryboardModel(
        language=language,
        narrations=[
            StoryboardNarration(
                narration_id=n.get("narrationId", i),
                text=n.get("text"),
                voice=n.get("voice"),
                translations=n.get("translations"),
            )
            for i, n in enumerate(narration_entries)
        ],
        options=StoryboardOptions(voices=voices_map) if voices_map else None,
    )

    if tts_backend is None:
        tts_backend = KokoroTTS()
    _generate_tts_audio(storyboard, audio_dir, tts_backend)

    segment_files: list[Path] = []
    audio_timestamps: list[int] = []
    cumulative_ms = 0

    for i, entry in enumerate(narration_entries):
        video_rel = entry.get("videoFile")
        if not video_rel:
            raise RuntimeError(f"Narration {i} has no videoFile entry")
        clip_path = target_dir / video_rel
        if not clip_path.exists():
            raise RuntimeError(f"Narration {i} video file not found: {clip_path}")

        clip_duration_ms = probe_duration_ms(clip_path)

        wav_file = audio_dir / _segment_name(i)
        audio_duration_ms = probe_duration_ms(wav_file) if wav_file.exists() else 0

        normalized_clip = temp_dir / f"clip_{i:03d}.mp4"
        exec_ffmpeg(
            "-y", "-i", str(clip_path),
            "-r", "25",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            str(normalized_clip),
        )

        audio_timestamps.append(cumulative_ms)

        freeze_needed_ms = audio_duration_ms - clip_duration_ms
        if freeze_needed_ms > 100:
            last_frame = temp_dir / f"freeze_{i:03d}.png"
            exec_ffmpeg(
                "-y", "-sseof", "-0.04", "-i", str(normalized_clip),
                "-vframes", "1", str(last_frame),
            )

            freeze_seg = temp_dir / f"freeze_seg_{i:03d}.mp4"
            exec_ffmpeg(
                "-y", "-r", "25", "-f", "image2", "-i", str(last_frame),
                "-vf", "loop=-1:1:0",
                "-t", secs(freeze_needed_ms / 1000.0),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an",
                str(freeze_seg),
            )

            combined = temp_dir / f"extended_{i:03d}.mp4"
            concat_list = temp_dir / f"concat_{i:03d}.txt"
            concat_list.write_text(
                f"file '{normalized_clip.resolve()}'\nfile '{freeze_seg.resolve()}'\n",
                encoding="utf-8",
            )
            exec_ffmpeg(
                "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an",
                str(combined),
            )
            segment_files.append(combined)
            cumulative_ms += clip_duration_ms + freeze_needed_ms
            log.info("Narration %d: clip=%dms, audio=%dms, freeze=%dms",
                     i, clip_duration_ms, audio_duration_ms, freeze_needed_ms)
        else:
            segment_files.append(normalized_clip)
            cumulative_ms += clip_duration_ms
            log.info("Narration %d: clip=%dms, audio=%dms", i, clip_duration_ms, audio_duration_ms)

    final_concat = temp_dir / "final_concat.txt"
    final_concat.write_text(
        "\n".join(f"file '{seg.resolve()}'" for seg in segment_files) + "\n",
        encoding="utf-8",
    )
    concatenated_video = temp_dir / "concatenated.mp4"
    exec_ffmpeg(
        "-y", "-f", "concat", "-safe", "0", "-i", str(final_concat),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an",
        str(concatenated_video),
    )

    narration_texts = [n.get("text", "") for n in narration_entries]
    narrations = [
        NarrationSegment(
            start_ms=audio_timestamps[i],
            end_ms=audio_timestamps[i] + (probe_duration_ms(target_dir / narration_entries[i]["videoFile"])
                                          if (target_dir / narration_entries[i]["videoFile"]).exists() else 0),
            text=narration_texts[i],
            audio_duration_ms=probe_duration_ms(audio_dir / _segment_name(i))
                              if (audio_dir / _segment_name(i)).exists() else 0,
        )
        for i in range(len(narration_entries))
    ]

    primary_srt = output_file.with_suffix(".srt")
    _write_srt(narrations, audio_timestamps, primary_srt)
    srt_files: list[tuple[Path, str]] = [(primary_srt, language)]

    translation_langs: set[str] = set()
    for sn in storyboard.narrations:
        if sn.translations:
            translation_langs.update(sn.translations.keys())
    for lang in sorted(translation_langs):
        lang_srt = output_file.with_name(f"{output_file.stem}_{lang}.srt")
        _write_srt(narrations, audio_timestamps, lang_srt, storyboard.narrations, lang)
        srt_files.append((lang_srt, lang))

    overlay: OverlayResult | None = None
    if debug_overlay:
        overlay = generate_overlay_filter(
            narrations, audio_timestamps, storyboard,
            temp_dir, font_size or 24,
        )

    _overlay_audio(
        concatenated_video, narrations, audio_timestamps, audio_dir, output_file,
        overlay=overlay, srt_files=srt_files,
    )

    _write_timeline(storyboard, narrations, audio_timestamps, target_dir)
    generate_timeline_html(target_dir)


def _segment_name(index: int) -> str:
    return f"segment_{index:03d}.wav"


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


def _write_timeline(
    storyboard: StoryboardModel,
    narrations: list[NarrationSegment],
    adjusted_timestamps: list[int],
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
        timeline_narrations.append(entry)

    data = {
        "narrations": timeline_narrations,
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
