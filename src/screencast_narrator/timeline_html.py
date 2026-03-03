"""Timeline HTML visualization: original, adjusted, and combined three-column views."""

from __future__ import annotations

import json
from pathlib import Path

from screencast_narrator.ffmpeg import probe_duration_ms
from screencast_narrator.freeze_frames import (
    FreezeFrameCalculator,
    GapCut,
    HighlightEntry,
    NarrationSegment,
    adjust_for_cuts,
    adjust_timestamp,
)

PX_PER_SECOND = 100.0
TIME_COL_WIDTH = 80
NARR_LANE_WIDTH = 320
ACTION_COL_WIDTH = 260
FREEZE_COL_WIDTH = 40
HL_COL_WIDTH = 60
HEADER_HEIGHT = 32

COLORS = [
    "#0891b2", "#7c3aed", "#059669", "#db2777",
    "#d97706", "#2563eb", "#dc2626", "#16a34a",
]


def _ms_to_y(ms: int) -> int:
    return int(ms / 1000.0 * PX_PER_SECOND)


def _fmt_time(ms: int) -> str:
    sec = ms // 1000
    frac = (ms % 1000) // 100
    return f"{sec // 60}:{sec % 60:02d}.{frac}"


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _append_grid_lines(lines: list[str], max_ms: int) -> None:
    for ms in range(0, max_ms + 1, 30000):
        lines.append(f'    <div class="grid-line major" style="top:{_ms_to_y(ms)}px;"></div>')
    for ms in range(0, max_ms + 1, 10000):
        if ms % 30000 != 0:
            lines.append(f'    <div class="grid-line" style="top:{_ms_to_y(ms)}px;"></div>')


def _assign_narration_lanes(narrations: list[dict]) -> list[int]:
    lanes: list[int] = []
    lane_ends: list[int] = []

    for n in narrations:
        start = n["timestampMs"]
        end = n.get("endTimestampMs", start)
        if start == end:
            end = start + 2000

        assigned_lane = -1
        for i, le in enumerate(lane_ends):
            if le <= start:
                assigned_lane = i
                break
        if assigned_lane == -1:
            assigned_lane = len(lane_ends)
            lane_ends.append(0)
        lanes.append(assigned_lane)
        lane_ends[assigned_lane] = end

    return lanes


def _read_timeline(target_dir: Path) -> tuple[dict, list[dict], list[dict], list[dict]]:
    timeline_file = target_dir / "timeline.json"
    root = json.loads(timeline_file.read_text())
    events = root.get("events", root if isinstance(root, list) else [])

    narrations: list[dict] = []
    highlights: list[dict] = []
    actions: list[dict] = []
    for event in events:
        t = event.get("type")
        if t == "narration":
            narrations.append(event)
        elif t == "highlight":
            highlights.append(event)
        elif t == "action":
            actions.append(event)

    narrations.sort(key=lambda n: n["timestampMs"])
    highlights.sort(key=lambda h: h["timestampMs"])
    actions.sort(key=lambda a: a["timestampMs"])

    return root, narrations, highlights, actions


_BASE_CSS = """
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #fff; color: #1a1a2e; padding: 24px;
  }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .subtitle {{ color: #6b7280; font-size: 13px; margin-bottom: 4px; }}
  .legend {{ color: #6b7280; font-size: 12px; margin-bottom: 20px; }}
  .legend span {{ display: inline-block; margin-right: 16px; }}
  .legend .swatch {{
    display: inline-block; width: 14px; height: 14px;
    vertical-align: middle; margin-right: 4px; border-radius: 2px;
  }}
  .timeline-container {{ display: flex; gap: 0; position: relative; }}
  .band {{ position: relative; flex-shrink: 0; }}
  .band-header {{
    position: sticky; top: 0; z-index: 10;
    background: #1e293b; color: #e2e8f0;
    font-size: 11px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
    padding: 8px 12px; height: {header_height}px;
    display: flex; align-items: center;
  }}
  .band-body {{ position: relative; height: {total_height}px; }}
  .time-band {{ width: {time_width}px; }}
  .time-band .band-body {{ background: #f8f9fa; border-right: 2px solid #cbd5e1; }}
  .freeze-band {{ width: {freeze_width}px; }}
  .freeze-band .band-body {{ background: #fefce8; border-right: 2px solid #cbd5e1; }}
  .narr-band .band-body {{ background: #fafbfc; border-right: 2px solid #cbd5e1; }}
  .action-band .band-body {{ background: #f0fdf4; border-right: 2px solid #cbd5e1; }}
  .hl-band .band-body {{ background: #fff5f5; }}

  .tick-line {{ position: absolute; left: 0; right: 0; border-top: 1px solid #e5e7eb; z-index: 1; }}
  .tick-line.major {{ border-top: 1px solid #94a3b8; }}
  .tick-label {{
    position: absolute; right: 8px; font-size: 10px; color: #94a3b8;
    transform: translateY(-50%); white-space: nowrap; font-variant-numeric: tabular-nums;
  }}
  .tick-label.major {{ color: #334155; font-weight: 700; font-size: 11px; }}

  .freeze-block {{
    position: absolute; left: 4px; right: 4px;
    background: repeating-linear-gradient(45deg, #fbbf24, #fbbf24 3px, #fef3c7 3px, #fef3c7 6px);
    border-radius: 2px; z-index: 2; min-height: 2px; border: 1px solid #f59e0b;
  }}
  .gap-cut-block {{
    position: absolute; left: 4px; right: 4px;
    background: repeating-linear-gradient(-45deg, #f87171, #f87171 3px, #fecaca 3px, #fecaca 6px);
    border-radius: 2px; z-index: 2; min-height: 2px; border: 1px solid #ef4444;
  }}

  .narr-block {{
    position: absolute; border-radius: 4px; padding: 5px 8px;
    font-size: 11px; line-height: 1.4; border-left: 4px solid; z-index: 2;
  }}
  .narr-time {{
    font-size: 10px; font-weight: 700; margin-bottom: 2px;
    white-space: nowrap; font-variant-numeric: tabular-nums;
  }}
  .narr-text {{ font-size: 11px; line-height: 1.35; word-wrap: break-word; }}
  .audio-bar {{
    position: absolute; left: 0; right: 0; bottom: 0;
    border-radius: 0 0 4px 0; opacity: 0.3; z-index: 1;
  }}

  .action-dot {{
    position: absolute; left: 4px; right: 4px; border-radius: 3px;
    padding: 2px 6px; font-size: 10px; line-height: 1.3; z-index: 2;
    border-left: 3px solid; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }}
  .action-time {{ font-size: 9px; font-weight: 600; font-variant-numeric: tabular-nums; margin-right: 4px; }}
  .action-desc {{ font-size: 10px; }}

  .hl-block {{
    position: absolute; left: 8px; right: 8px;
    background: #fecdd3; border-radius: 2px; border-left: 3px solid #fb7185;
    z-index: 2; min-height: 2px;
  }}

  .grid-line {{
    position: absolute; left: 0; right: 0; border-top: 1px dashed #f0f0f0;
    pointer-events: none; z-index: 0;
  }}
  .grid-line.major {{ border-top: 1px dashed #e0e0e0; }}
"""


def _build_narration_color_map(narrations: list[dict]) -> dict[int, str]:
    color_map: dict[int, str] = {}
    for i, n in enumerate(narrations):
        nid = n.get("narrationId", i)
        color_map[nid] = COLORS[i % len(COLORS)]
    return color_map


def _render_time_ruler(lines: list[str], max_ms: int, step: int = 5000) -> None:
    lines.append('<div class="band time-band">')
    lines.append('  <div class="band-header">Time</div>')
    lines.append('  <div class="band-body">')
    for ms in range(0, max_ms + 1, step):
        y = _ms_to_y(ms)
        major = " major" if ms % 30000 == 0 else ""
        lines.append(f'    <div class="tick-line{major}" style="top:{y}px;"></div>')
        if ms % 10000 == 0 or step <= 1000:
            lines.append(f'    <div class="tick-label{major}" style="top:{y}px;">{_fmt_time(ms)}</div>')
    lines.append('  </div>\n</div>')


def _render_narrations_band(
    lines: list[str], narrations: list[dict], max_ms: int,
    lane_count: int = 1, lane_assignments: list[int] | None = None,
) -> None:
    lines.append(f'<div class="band narr-band" style="width:{lane_count * NARR_LANE_WIDTH}px;">')
    lines.append(f'  <div class="band-header">Narrations ({len(narrations)})</div>')
    lines.append('  <div class="band-body">')
    _append_grid_lines(lines, max_ms)

    for i, n in enumerate(narrations):
        start = n["timestampMs"]
        end = n.get("endTimestampMs", start)
        is_zero = start == end
        color = COLORS[i % len(COLORS)]
        text = _escape_html(n["text"])
        y = _ms_to_y(start)
        est_text_h = 16 + (len(text) // 40) * 14 + 14
        h = est_text_h if is_zero else max(_ms_to_y(end) - y, est_text_h)
        bg = _hex_to_rgba(color, 0.1)

        lane = lane_assignments[i] if lane_assignments else 0
        left = lane * NARR_LANE_WIDTH + 4
        width = NARR_LANE_WIDTH - 8

        dur_label = "instant" if is_zero else f"{(end - start) / 1000.0:.1f}s"
        time_label = (f"{_fmt_time(start)} (instant)" if is_zero
                      else f"{_fmt_time(start)} \u2192 {_fmt_time(end)} ({dur_label})")

        lines.append(f'    <div class="narr-block" style="top:{y}px;height:{h}px;left:{left}px;width:{width}px;background:{bg};border-color:{color};">')
        lines.append(f'      <div class="narr-time" style="color:{color};">N{i:02d} &middot; {time_label}</div>')
        lines.append(f'      <div class="narr-text">{text}</div>')
        lines.append('    </div>')

    lines.append('  </div>\n</div>')


def _render_actions_band(
    lines: list[str], actions: list[dict], max_ms: int,
    narration_color_map: dict[int, str],
) -> None:
    lines.append(f'<div class="band action-band" style="width:{ACTION_COL_WIDTH}px;">')
    lines.append(f'  <div class="band-header">Screen Actions ({len(actions)})</div>')
    lines.append('  <div class="band-body">')
    _append_grid_lines(lines, max_ms)

    last_bottom = 0
    for action in actions:
        ts = action["timestampMs"]
        desc = _escape_html(action["description"])
        nid = action.get("narrationId", -1)
        color = narration_color_map.get(nid, "#6b7280")
        bg = _hex_to_rgba(color, 0.08)
        y = max(_ms_to_y(ts), last_bottom + 1)
        h = 14
        last_bottom = y + h
        lines.append(f'    <div class="action-dot" style="top:{y}px;height:{h}px;background:{bg};border-color:{color};" title="{desc} at {_fmt_time(ts)}">')
        lines.append(f'      <span class="action-time" style="color:{color};">{_fmt_time(ts)}</span>')
        lines.append(f'      <span class="action-desc">{desc}</span>')
        lines.append('    </div>')

    lines.append('  </div>\n</div>')


def _render_highlights_band(
    lines: list[str], highlights: list[dict], max_ms: int,
    narration_color_map: dict[int, str],
) -> None:
    lines.append(f'<div class="band hl-band" style="width:{HL_COL_WIDTH}px;">')
    lines.append('  <div class="band-header">HL</div>')
    lines.append('  <div class="band-body">')
    _append_grid_lines(lines, max_ms)

    for hl in highlights:
        start = hl["timestampMs"]
        end = hl["endTimestampMs"]
        nid = hl.get("narrationId", -1)
        color = narration_color_map.get(nid, "#fb7185")
        y = _ms_to_y(start)
        h = max(_ms_to_y(end) - y, 3)
        lines.append(f'    <div class="hl-block" style="top:{y}px;height:{h}px;background:{_hex_to_rgba(color, 0.3)};border-color:{color};"></div>')

    lines.append('  </div>\n</div>')


# --- Original timeline ---

def generate_original_html(target_dir: Path) -> Path:
    _root, narrations, highlights, actions = _read_timeline(target_dir)

    max_ms = 0
    for n in narrations:
        max_ms = max(max_ms, n.get("endTimestampMs", n["timestampMs"]))
    for h in highlights:
        max_ms = max(max_ms, h["endTimestampMs"])
    for a in actions:
        max_ms = max(max_ms, a["timestampMs"])

    narr_lanes = _assign_narration_lanes(narrations)
    max_lane = max(narr_lanes, default=0)
    lane_count = max_lane + 1
    total_height = _ms_to_y(max_ms) + 60
    narration_color_map = _build_narration_color_map(narrations)

    css = _BASE_CSS.format(
        header_height=HEADER_HEIGHT, total_height=total_height,
        time_width=TIME_COL_WIDTH, freeze_width=FREEZE_COL_WIDTH,
    )

    lines: list[str] = []
    lines.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">')
    lines.append(f'<title>Screencast Timeline</title><style>{css}</style></head><body>')
    lines.append(f'<h1>Screencast &mdash; Original Video Timeline</h1>')
    lines.append(f'<p class="subtitle">{len(narrations)} narrations &middot; {len(actions)} actions &middot; {len(highlights)} highlights &middot; Total: {_fmt_time(max_ms)}</p>')
    lines.append('<div class="timeline-container">')

    _render_time_ruler(lines, max_ms)
    _render_narrations_band(lines, narrations, max_ms, lane_count, narr_lanes)
    _render_actions_band(lines, actions, max_ms, narration_color_map)
    _render_highlights_band(lines, highlights, max_ms, narration_color_map)

    lines.append('</div></body></html>')

    output_file = target_dir / "timeline-original.html"
    output_file.write_text("\n".join(lines))
    return output_file


# --- Adjusted timeline ---

def generate_adjusted_html(target_dir: Path) -> Path:
    root, narration_nodes, highlight_nodes, action_nodes = _read_timeline(target_dir)
    audio_dir = target_dir / "narration-audio"

    hl_entries = [
        HighlightEntry(h["timestampMs"], h["endTimestampMs"] - h["timestampMs"])
        for h in highlight_nodes
    ]

    narration_segments: list[NarrationSegment] = []
    for i, n in enumerate(narration_nodes):
        start = n["timestampMs"]
        end = n.get("endTimestampMs", start)
        audio_dur = _probe_audio_duration(audio_dir, i)
        narration_segments.append(NarrationSegment(start, end, n["text"], audio_dur))

    result = FreezeFrameCalculator(narration_segments, hl_entries).calculate()
    freeze_frames = sorted(result.freeze_frames, key=lambda f: f.time_ms)
    adjusted_starts = result.adjusted_timestamps
    total_freeze_ms = sum(f.duration_ms for f in freeze_frames)

    orig_max = 0
    for n in narration_segments:
        orig_max = max(orig_max, n.end_ms)
    for h in highlight_nodes:
        orig_max = max(orig_max, h["endTimestampMs"])
    for a in action_nodes:
        orig_max = max(orig_max, a["timestampMs"])
    adj_max = orig_max + total_freeze_ms + 5000
    for i, ns in enumerate(narration_segments):
        adj_max = max(adj_max, adjusted_starts[i] + ns.audio_duration_ms)

    narration_color_map = _build_narration_color_map(narration_nodes)
    total_height = _ms_to_y(adj_max) + 60

    css = _BASE_CSS.format(
        header_height=HEADER_HEIGHT, total_height=total_height,
        time_width=TIME_COL_WIDTH, freeze_width=FREEZE_COL_WIDTH,
    )

    lines: list[str] = []
    lines.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">')
    lines.append(f'<title>Screencast — Adjusted Timeline</title><style>{css}</style></head><body>')
    lines.append(f'<h1>Screencast &mdash; Adjusted Timeline (Final Video)</h1>')
    lines.append(f'<p class="subtitle">{len(narration_segments)} narrations &middot; {len(action_nodes)} actions &middot; {len(freeze_frames)} freeze-frames ({_fmt_time(total_freeze_ms)} frozen) &middot; Total: {_fmt_time(adj_max)}</p>')
    lines.append('<p class="legend">')
    lines.append('  <span><span class="swatch" style="background:repeating-linear-gradient(45deg,#fbbf24,#fbbf24 2px,#fef3c7 2px,#fef3c7 4px);border:1px solid #f59e0b;"></span>Freeze frame</span>')
    lines.append('  <span><span class="swatch" style="background:rgba(8,145,178,0.25);"></span>Audio playing</span>')
    lines.append('</p>')
    lines.append('<div class="timeline-container">')

    _render_time_ruler(lines, adj_max, step=1000)

    # Freeze frame band
    lines.append(f'<div class="band freeze-band">')
    lines.append('  <div class="band-header">FF</div>')
    lines.append('  <div class="band-body">')
    _append_grid_lines(lines, adj_max)
    for ff in freeze_frames:
        adj_time = adjust_timestamp(ff.time_ms, freeze_frames)
        y = _ms_to_y(adj_time)
        h = max(_ms_to_y(adj_time + ff.duration_ms) - y, 3)
        lines.append(f'    <div class="freeze-block" style="top:{y}px;height:{h}px;" title="Freeze at {_fmt_time(ff.time_ms)} for {_fmt_time(ff.duration_ms)}"></div>')
    lines.append('  </div>\n</div>')

    # Narrations (adjusted)
    lines.append(f'<div class="band narr-band" style="width:{NARR_LANE_WIDTH}px;">')
    lines.append(f'  <div class="band-header">Narrations ({len(narration_segments)})</div>')
    lines.append('  <div class="band-body">')
    _append_grid_lines(lines, adj_max)
    for i, ns in enumerate(narration_segments):
        adj_start = adjusted_starts[i]
        audio_dur = ns.audio_duration_ms
        color = COLORS[i % len(COLORS)]
        text = _escape_html(ns.text)
        y = _ms_to_y(adj_start)
        audio_h = max(_ms_to_y(adj_start + audio_dur) - y, 4)
        est_text_h = 16 + (len(text) // 40) * 14 + 14
        block_h = max(audio_h, est_text_h)
        bg = _hex_to_rgba(color, 0.1)
        is_zero = ns.start_ms == ns.end_ms
        bracket_dur = ns.end_ms - ns.start_ms
        orig_label = (f"orig {_fmt_time(ns.start_ms)} (instant)" if is_zero
                      else f"orig {_fmt_time(ns.start_ms)}\u2192{_fmt_time(ns.end_ms)} ({bracket_dur / 1000.0:.1f}s)")
        time_label = f"adj {_fmt_time(adj_start)}  audio {audio_dur / 1000.0:.1f}s  {orig_label}"

        lines.append(f'    <div class="narr-block" style="top:{y}px;height:{block_h}px;left:4px;width:{NARR_LANE_WIDTH - 8}px;background:{bg};border-color:{color};">')
        lines.append(f'      <div class="audio-bar" style="top:0;height:{audio_h}px;background:{_hex_to_rgba(color, 0.25)};"></div>')
        lines.append(f'      <div class="narr-time" style="color:{color};">N{i:02d} &middot; {time_label}</div>')
        lines.append(f'      <div class="narr-text">{text}</div>')
        lines.append('    </div>')
    lines.append('  </div>\n</div>')

    # Actions (adjusted)
    adjusted_actions = []
    for a in action_nodes:
        adj_a = dict(a)
        adj_a["timestampMs"] = adjust_timestamp(a["timestampMs"], freeze_frames)
        adjusted_actions.append(adj_a)
    _render_actions_band(lines, adjusted_actions, adj_max, narration_color_map)

    # Highlights (adjusted)
    adjusted_hls = []
    for h in highlight_nodes:
        adj_h = dict(h)
        adj_h["timestampMs"] = adjust_timestamp(h["timestampMs"], freeze_frames)
        adj_h["endTimestampMs"] = adjust_timestamp(h["endTimestampMs"], freeze_frames)
        adjusted_hls.append(adj_h)
    _render_highlights_band(lines, adjusted_hls, adj_max, narration_color_map)

    lines.append('</div></body></html>')

    output_file = target_dir / "timeline-adjusted.html"
    output_file.write_text("\n".join(lines))
    return output_file


# --- Combined three-column timeline ---

def generate_combined_html(target_dir: Path) -> Path:
    root, narration_nodes, highlight_nodes, action_nodes = _read_timeline(target_dir)
    audio_dir = target_dir / "narration-audio"

    hl_entries = [
        HighlightEntry(h["timestampMs"], h["endTimestampMs"] - h["timestampMs"])
        for h in highlight_nodes
    ]

    narration_segments: list[NarrationSegment] = []
    for i, n in enumerate(narration_nodes):
        start = n["timestampMs"]
        end = n.get("endTimestampMs", start)
        audio_dur = _probe_audio_duration(audio_dir, i)
        narration_segments.append(NarrationSegment(start, end, n["text"], audio_dur))

    video_offset = root.get("videoRecordingStartedAtMs", 0)
    video_recording_end = root.get("videoRecordingEndedAtMs", 2**63 - 1)
    result = FreezeFrameCalculator(narration_segments, hl_entries, video_recording_end).calculate()
    freeze_frames = sorted(result.freeze_frames, key=lambda f: f.time_ms)
    adjusted_starts = result.adjusted_timestamps

    gap_cuts: list[GapCut] = []
    gap_cuts_file = target_dir / "gap-cuts.json"
    if gap_cuts_file.exists():
        raw = json.loads(gap_cuts_file.read_text())
        gap_cuts = [GapCut(g["startMs"], g["endMs"]) for g in raw]

    total_freeze_ms = sum(f.duration_ms for f in freeze_frames)
    total_cut_ms = sum(g.end_ms - g.start_ms for g in gap_cuts)

    orig_max = 0
    for ns in narration_segments:
        orig_max = max(orig_max, ns.end_ms)
    for h in highlight_nodes:
        orig_max = max(orig_max, h["endTimestampMs"])
    adj_max = orig_max + total_freeze_ms + 5000
    for i, ns in enumerate(narration_segments):
        adj_max = max(adj_max, adjusted_starts[i] + ns.audio_duration_ms)
    final_max = max(0, adj_max - total_cut_ms)

    global_max = max(orig_max, adj_max, final_max)
    total_height = _ms_to_y(global_max) + 60

    css = _BASE_CSS.format(
        header_height=HEADER_HEIGHT, total_height=total_height,
        time_width=TIME_COL_WIDTH, freeze_width=FREEZE_COL_WIDTH,
    )

    lines: list[str] = []
    lines.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">')
    lines.append(f'<title>Screencast — Combined Timeline</title><style>{css}\n.column-sep {{ border-left: 4px solid #1e293b; }}</style></head><body>')
    lines.append(f'<h1>Screencast &mdash; Timeline Comparison</h1>')
    lines.append(f'<p class="subtitle">{len(narration_segments)} narrations &middot; {len(freeze_frames)} freeze-frames ({_fmt_time(total_freeze_ms)}) &middot; {len(gap_cuts)} gap cuts ({_fmt_time(total_cut_ms)})</p>')
    lines.append('<p class="legend">')
    lines.append('  <span><span class="swatch" style="background:repeating-linear-gradient(45deg,#fbbf24,#fbbf24 2px,#fef3c7 2px,#fef3c7 4px);border:1px solid #f59e0b;"></span>Freeze frame</span>')
    lines.append('  <span><span class="swatch" style="background:repeating-linear-gradient(-45deg,#f87171,#f87171 2px,#fecaca 2px,#fecaca 4px);border:1px solid #ef4444;"></span>Gap cut</span>')
    lines.append('</p>')
    lines.append('<div class="timeline-container">')

    narration_color_map = _build_narration_color_map(narration_nodes)

    # Column 1: Original
    _render_time_ruler(lines, global_max)
    narr_lanes = _assign_narration_lanes(narration_nodes)
    _render_narrations_band(lines, narration_nodes, global_max, 1, [0] * len(narration_nodes))
    _render_actions_band(lines, action_nodes, global_max, narration_color_map)
    _render_highlights_band(lines, highlight_nodes, global_max, narration_color_map)

    # Column 2: Adjusted (with freeze frames)
    lines.append(f'<div class="band column-sep" style="width:4px;"><div class="band-header" style="background:#0f172a;"></div><div class="band-body"></div></div>')
    _render_time_ruler(lines, global_max, step=1000)

    # FF band
    lines.append(f'<div class="band freeze-band">')
    lines.append('  <div class="band-header">FF</div>')
    lines.append('  <div class="band-body">')
    for ff in freeze_frames:
        adj_time = adjust_timestamp(ff.time_ms, freeze_frames)
        y = _ms_to_y(adj_time)
        h = max(_ms_to_y(adj_time + ff.duration_ms) - y, 3)
        lines.append(f'    <div class="freeze-block" style="top:{y}px;height:{h}px;"></div>')
    lines.append('  </div>\n</div>')

    # Adjusted narrations
    adj_narr_nodes = []
    for i, ns in enumerate(narration_segments):
        adj_narr_nodes.append({
            "timestampMs": adjusted_starts[i],
            "endTimestampMs": adjusted_starts[i] + ns.audio_duration_ms,
            "text": ns.text,
            "narrationId": narration_nodes[i].get("narrationId", i),
        })
    _render_narrations_band(lines, adj_narr_nodes, global_max)

    adj_action_nodes = [dict(a, timestampMs=adjust_timestamp(a["timestampMs"], freeze_frames)) for a in action_nodes]
    _render_actions_band(lines, adj_action_nodes, global_max, narration_color_map)

    adj_hl_nodes = [dict(h, timestampMs=adjust_timestamp(h["timestampMs"], freeze_frames),
                         endTimestampMs=adjust_timestamp(h["endTimestampMs"], freeze_frames))
                    for h in highlight_nodes]
    _render_highlights_band(lines, adj_hl_nodes, global_max, narration_color_map)

    # Column 3: Final (after gap cuts)
    if gap_cuts:
        lines.append(f'<div class="band column-sep" style="width:4px;"><div class="band-header" style="background:#0f172a;"></div><div class="band-body"></div></div>')
        _render_time_ruler(lines, global_max, step=1000)

        # Gap cut band
        lines.append(f'<div class="band freeze-band">')
        lines.append('  <div class="band-header">GC</div>')
        lines.append('  <div class="band-body">')
        for gc in gap_cuts:
            y = _ms_to_y(gc.start_ms)
            h = max(_ms_to_y(gc.end_ms) - y, 3)
            lines.append(f'    <div class="gap-cut-block" style="top:{y}px;height:{h}px;"></div>')
        lines.append('  </div>\n</div>')

        final_narr_nodes = []
        for i, ns in enumerate(narration_segments):
            final_ts = adjust_for_cuts(adjusted_starts[i], gap_cuts)
            final_narr_nodes.append({
                "timestampMs": final_ts,
                "endTimestampMs": final_ts + ns.audio_duration_ms,
                "text": ns.text,
                "narrationId": narration_nodes[i].get("narrationId", i),
            })
        _render_narrations_band(lines, final_narr_nodes, global_max)

        final_action_nodes = [dict(a, timestampMs=adjust_for_cuts(adjust_timestamp(a["timestampMs"], freeze_frames), gap_cuts))
                              for a in action_nodes]
        _render_actions_band(lines, final_action_nodes, global_max, narration_color_map)

        final_hl_nodes = [dict(h, timestampMs=adjust_for_cuts(adjust_timestamp(h["timestampMs"], freeze_frames), gap_cuts),
                               endTimestampMs=adjust_for_cuts(adjust_timestamp(h["endTimestampMs"], freeze_frames), gap_cuts))
                          for h in highlight_nodes]
        _render_highlights_band(lines, final_hl_nodes, global_max, narration_color_map)

    lines.append('</div></body></html>')

    output_file = target_dir / "timeline-combined.html"
    output_file.write_text("\n".join(lines))
    return output_file


def _probe_audio_duration(audio_dir: Path, index: int) -> int:
    wav_file = audio_dir / f"segment_{index:03d}.wav"
    if not wav_file.exists():
        return 0
    return probe_duration_ms(wav_file)
