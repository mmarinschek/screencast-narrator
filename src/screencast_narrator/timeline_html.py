"""Timeline HTML visualization: reads timeline.json to produce visual timelines."""

from __future__ import annotations

import json
from pathlib import Path

PX_PER_SECOND = 100.0
TIME_COL_WIDTH = 80
NARR_LANE_WIDTH = 320
HEADER_HEIGHT = 32

COLORS = [
    "#0891b2",
    "#7c3aed",
    "#059669",
    "#db2777",
    "#d97706",
    "#2563eb",
    "#dc2626",
    "#16a34a",
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
  .narr-band .band-body {{ background: #fafbfc; border-right: 2px solid #cbd5e1; }}

  .tick-line {{ position: absolute; left: 0; right: 0; border-top: 1px solid #e5e7eb; z-index: 1; }}
  .tick-line.major {{ border-top: 1px solid #94a3b8; }}
  .tick-label {{
    position: absolute; right: 8px; font-size: 10px; color: #94a3b8;
    transform: translateY(-50%); white-space: nowrap; font-variant-numeric: tabular-nums;
  }}
  .tick-label.major {{ color: #334155; font-weight: 700; font-size: 11px; }}

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

  .grid-line {{
    position: absolute; left: 0; right: 0; border-top: 1px dashed #f0f0f0;
    pointer-events: none; z-index: 0;
  }}
  .grid-line.major {{ border-top: 1px dashed #e0e0e0; }}
"""


def _read_timeline(target_dir: Path) -> dict:
    timeline_file = target_dir / "timeline.json"
    return json.loads(timeline_file.read_text(encoding="utf-8"))


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
    lines.append("  </div>\n</div>")


def _render_narrations_band(
    lines: list[str],
    narration_entries: list[dict],
    max_ms: int,
) -> None:
    lines.append(f'<div class="band narr-band" style="width:{NARR_LANE_WIDTH}px;">')
    lines.append(f'  <div class="band-header">Narrations ({len(narration_entries)})</div>')
    lines.append('  <div class="band-body">')
    _append_grid_lines(lines, max_ms)

    for i, n in enumerate(narration_entries):
        start = n["startMs"]
        end = n["endMs"]
        audio_dur = n.get("audioDurationMs", 0)
        color = COLORS[i % len(COLORS)]
        text = _escape_html(n["text"])
        y = _ms_to_y(start)
        est_text_h = 16 + (len(text) // 40) * 14 + 14
        block_h = max(_ms_to_y(end) - y, est_text_h)

        audio_h = max(_ms_to_y(start + audio_dur) - y, 4) if audio_dur > 0 else 0
        block_h = max(block_h, audio_h)

        bg = _hex_to_rgba(color, 0.1)
        dur_label = f"{(end - start) / 1000.0:.1f}s"
        time_label = f"{_fmt_time(start)} \u2192 {_fmt_time(end)} ({dur_label})  audio {audio_dur / 1000.0:.1f}s"

        lines.append(
            f'    <div class="narr-block" style="top:{y}px;height:{block_h}px;left:4px;width:{NARR_LANE_WIDTH - 8}px;background:{bg};border-color:{color};">'
        )
        if audio_h > 0:
            lines.append(
                f'      <div class="audio-bar" style="top:0;height:{audio_h}px;background:{_hex_to_rgba(color, 0.25)};"></div>'
            )
        lines.append(f'      <div class="narr-time" style="color:{color};">N{i:02d} &middot; {time_label}</div>')
        lines.append(f'      <div class="narr-text">{text}</div>')
        lines.append("    </div>")

    lines.append("  </div>\n</div>")


def generate_timeline_html(target_dir: Path) -> Path:
    timeline = _read_timeline(target_dir)
    narrations = timeline["narrations"]

    entries = [
        {
            "startMs": n["timestampMs"],
            "endMs": n["timestampMs"] + n["audioDurationMs"],
            "text": n["text"],
            "audioDurationMs": n["audioDurationMs"],
        }
        for n in narrations
    ]

    max_ms = max((e["endMs"] for e in entries), default=0) + 2000
    total_height = _ms_to_y(max_ms) + 60

    css = _BASE_CSS.format(
        header_height=HEADER_HEIGHT,
        total_height=total_height,
        time_width=TIME_COL_WIDTH,
    )

    lines: list[str] = []
    lines.append('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">')
    lines.append(f"<title>Screencast — Timeline</title><style>{css}</style></head><body>")
    lines.append("<h1>Screencast &mdash; Timeline</h1>")
    lines.append(f'<p class="subtitle">{len(narrations)} narrations</p>')
    lines.append('<p class="legend">')
    lines.append('  <span><span class="swatch" style="background:rgba(8,145,178,0.25);"></span>Audio playing</span>')
    lines.append("</p>")
    lines.append('<div class="timeline-container">')

    _render_time_ruler(lines, max_ms)
    _render_narrations_band(lines, entries, max_ms)

    lines.append("</div></body></html>")

    output_file = target_dir / "timeline.html"
    output_file.write_text("\n".join(lines), encoding="utf-8")
    return output_file
