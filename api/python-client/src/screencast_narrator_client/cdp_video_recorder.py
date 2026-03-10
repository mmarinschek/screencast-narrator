"""CDP-based video recorder: captures frames via Chrome DevTools Protocol and pipes to ffmpeg."""

from __future__ import annotations

import base64
import logging
import subprocess
from pathlib import Path

from screencast_narrator_client.shared_config import SharedConfig

log = logging.getLogger(__name__)


class CdpVideoRecorder:
    def __init__(self, page, output_file: Path, width: int, height: int, config: SharedConfig) -> None:
        self._page = page
        self._output_file = output_file
        self._width = width
        self._height = height
        self._config = config
        self._cdp_session = None
        self._ffmpeg_process: subprocess.Popen | None = None
        self._recording = False
        self._frame_count = 0

    def start(self) -> None:
        self._output_file.parent.mkdir(parents=True, exist_ok=True)
        rec = self._config.recording

        self._ffmpeg_process = subprocess.Popen(
            self._config.ffmpeg_args(str(self._output_file)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        self._cdp_session = self._page.context.new_cdp_session(self._page)
        self._recording = True
        self._frame_count = 0

        self._cdp_session.on("Page.screencastFrame", self._on_frame)
        self._cdp_session.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": rec.jpeg_quality,
            "maxWidth": self._width,
            "maxHeight": self._height,
            "everyNthFrame": 1,
        })

        self._wait_for_min_frames()
        log.info("CDP screencast recording started: %s (%dx%d, %d initial frames)",
                 self._output_file, self._width, self._height, self._frame_count)

    def _on_frame(self, event: dict) -> None:
        if not self._recording:
            return
        data = event["data"]
        session_id = event["sessionId"]
        frame_bytes = base64.b64decode(data)
        assert self._ffmpeg_process is not None and self._ffmpeg_process.stdin is not None
        self._ffmpeg_process.stdin.write(frame_bytes)
        self._ffmpeg_process.stdin.flush()
        self._frame_count += 1
        self._cdp_session.send("Page.screencastFrameAck", {"sessionId": session_id})

    def _wait_for_min_frames(self) -> None:
        rec = self._config.recording
        max_waits = 50
        for _ in range(max_waits):
            if self._frame_count >= rec.min_frames:
                break
            self._page.wait_for_timeout(rec.min_frame_wait_ms)
        if self._frame_count < 1:
            raise RuntimeError(
                f"CDP screencast: no frames received after {max_waits * rec.min_frame_wait_ms}ms")

    def stop(self) -> None:
        if not self._recording:
            return
        rec = self._config.recording

        if self._frame_count < rec.min_frames:
            waits = (rec.min_frames - self._frame_count) * 2
            for _ in range(waits):
                if self._frame_count >= rec.min_frames:
                    break
                self._page.wait_for_timeout(rec.min_frame_wait_ms)

        self._recording = False
        self._cdp_session.send("Page.stopScreencast")
        self._page.wait_for_timeout(rec.stop_settle_ms)

        assert self._ffmpeg_process is not None and self._ffmpeg_process.stdin is not None
        self._ffmpeg_process.stdin.close()
        self._ffmpeg_process.wait(timeout=30)

        if self._ffmpeg_process.returncode != 0:
            output = self._ffmpeg_process.stdout.read().decode() if self._ffmpeg_process.stdout else ""
            raise RuntimeError(
                f"ffmpeg exited with code {self._ffmpeg_process.returncode} "
                f"(frames={self._frame_count}): {output}"
            )

        self._cdp_session.detach()
        log.info("CDP screencast recording stopped: %s (%d frames captured)",
                 self._output_file, self._frame_count)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def output_file(self) -> Path:
        return self._output_file
