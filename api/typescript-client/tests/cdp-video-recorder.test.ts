import { describe, it, expect, beforeAll } from "vitest";
import { execFileSync } from "child_process";
import { mkdtempSync, readFileSync, statSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import type { CDPSession, Page } from "playwright";
import { CdpVideoRecorder } from "../src/cdp-video-recorder.js";
import { loadSharedConfig } from "../src/index.js";

let frameJpeg: Buffer;

beforeAll(() => {
  const dir = mkdtempSync(join(tmpdir(), "cdp-recorder-test-"));
  const jpegPath = join(dir, "frame.jpg");
  execFileSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1",
    "-frames:v", "1", jpegPath,
  ]);
  frameJpeg = readFileSync(jpegPath);
});

function makeFakePage(framesToEmit: number): Page {
  let handler: ((event: Record<string, unknown>) => void) | null = null;
  const session = {
    on(_event: string, h: (event: Record<string, unknown>) => void) {
      handler = h;
    },
    off() {
      handler = null;
    },
    async send(method: string) {
      if (method === "Page.startScreencast") {
        for (let i = 0; i < framesToEmit; i++) {
          handler?.({ data: frameJpeg.toString("base64"), sessionId: i });
        }
      }
    },
    async detach() {},
  };
  const page = {
    context() {
      return {
        async newCDPSession() {
          return session as unknown as CDPSession;
        },
      };
    },
    async waitForTimeout(_ms: number) {},
  };
  return page as unknown as Page;
}

function probeFrameCount(file: string): number {
  const out = execFileSync("ffprobe", [
    "-v", "error", "-count_frames",
    "-show_entries", "stream=nb_read_frames",
    "-of", "csv=p=0", file,
  ]);
  return parseInt(out.toString().trim(), 10);
}

describe("CdpVideoRecorder", () => {
  it("pads recordings with fewer than 5 frames by repeating the last frame", async () => {
    const dir = mkdtempSync(join(tmpdir(), "cdp-recorder-test-"));
    const outputFile = join(dir, "short.mp4");
    const recorder = new CdpVideoRecorder(makeFakePage(2), outputFile, 64, 64, loadSharedConfig());

    await recorder.start();
    expect(recorder.frameCount).toBe(2);
    await recorder.stop();

    expect(recorder.frameCount).toBe(5);
    expect(statSync(outputFile).size).toBeGreaterThan(0);
    // ffmpeg encodes N or N-1 frames from N piped frames depending on version
    // (-r 25 timestamp rounding drops the last frame on e.g. ffmpeg 6.x)
    expect([4, 5]).toContain(probeFrameCount(outputFile));
  });

  it("does not pad recordings that already have enough frames", async () => {
    const dir = mkdtempSync(join(tmpdir(), "cdp-recorder-test-"));
    const outputFile = join(dir, "long.mp4");
    const recorder = new CdpVideoRecorder(makeFakePage(6), outputFile, 64, 64, loadSharedConfig());

    await recorder.start();
    await recorder.stop();

    expect(recorder.frameCount).toBe(6);
    expect([5, 6]).toContain(probeFrameCount(outputFile));
  });
});
