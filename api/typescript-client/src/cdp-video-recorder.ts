import { CDPSession, Page } from "playwright";
import { spawn, ChildProcess } from "child_process";
import { mkdirSync } from "fs";
import { dirname } from "path";
import { SharedConfig } from "./index.js";

const MAX_FRAME_WAIT_ITERATIONS = 50;
const FRAME_WAIT_MULTIPLIER = 2;
// Some ffmpeg builds fail to finalize a video from fewer than 5 piped frames.
const MIN_ENCODE_FRAMES = 5;

export class CdpVideoRecorder {
  private readonly page: Page;
  private readonly outputFile: string;
  private readonly width: number;
  private readonly height: number;
  private readonly config: SharedConfig;
  private cdpSession: CDPSession | null = null;
  private ffmpegProcess: ChildProcess | null = null;
  private recording = false;
  private _frameCount = 0;
  private lastFrameBytes: Buffer | null = null;
  private frameHandler: ((event: Record<string, unknown>) => void) | null = null;

  constructor(page: Page, outputFile: string, width: number, height: number, config: SharedConfig) {
    this.page = page;
    this.outputFile = outputFile;
    this.width = width;
    this.height = height;
    this.config = config;
  }

  async start(): Promise<void> {
    mkdirSync(dirname(this.outputFile), { recursive: true });

    const args = this.config.ffmpegArgs(this.outputFile);
    this.ffmpegProcess = spawn(args[0], args.slice(1), { stdio: ["pipe", "pipe", "pipe"] });

    this.cdpSession = await this.page.context().newCDPSession(this.page);
    this.recording = true;
    this._frameCount = 0;

    this.frameHandler = (event) => {
      if (!this.recording) return;
      const data = event.data as string;
      const sessionId = event.sessionId as number;
      const frameBytes = Buffer.from(data, "base64");
      if (this.ffmpegProcess?.stdin?.writable) {
        this.ffmpegProcess.stdin.write(frameBytes);
      }
      this.lastFrameBytes = frameBytes;
      this._frameCount++;
      this.cdpSession!.send("Page.screencastFrameAck", { sessionId });
    };
    this.cdpSession.on("Page.screencastFrame", this.frameHandler);

    const rec = this.config.recording;
    await this.cdpSession.send("Page.startScreencast", {
      format: "jpeg",
      quality: rec.jpegQuality,
      maxWidth: this.width,
      maxHeight: this.height,
      everyNthFrame: 1,
    });

    await this.waitForMinFrames();
  }

  private async waitForMinFrames(): Promise<void> {
    const rec = this.config.recording;
    for (let i = 0; i < MAX_FRAME_WAIT_ITERATIONS && this._frameCount < rec.minFrames; i++) {
      await this.page.waitForTimeout(rec.minFrameWaitMs);
    }
    if (this._frameCount < 1) {
      throw new Error(`CDP screencast: no frames received after ${MAX_FRAME_WAIT_ITERATIONS * rec.minFrameWaitMs}ms`);
    }
  }

  async stop(): Promise<void> {
    if (!this.recording) return;
    const rec = this.config.recording;

    if (this._frameCount < rec.minFrames) {
      const waits = (rec.minFrames - this._frameCount) * FRAME_WAIT_MULTIPLIER;
      for (let i = 0; i < waits && this._frameCount < rec.minFrames; i++) {
        await this.page.waitForTimeout(rec.minFrameWaitMs);
      }
    }

    this.recording = false;
    if (this.frameHandler) {
      this.cdpSession!.off("Page.screencastFrame", this.frameHandler);
      this.frameHandler = null;
    }
    await this.cdpSession!.send("Page.stopScreencast");
    await this.page.waitForTimeout(rec.stopSettleMs);

    await new Promise<void>((resolve, reject) => {
      if (!this.ffmpegProcess?.stdin) {
        resolve();
        return;
      }
      if (this.ffmpegProcess?.stdin?.writable && this.lastFrameBytes != null) {
        while (this._frameCount < MIN_ENCODE_FRAMES) {
          this.ffmpegProcess.stdin.write(this.lastFrameBytes);
          this._frameCount++;
        }
        this.lastFrameBytes = null;
      }
      this.ffmpegProcess.stdin.end(() => {
        this.ffmpegProcess!.on("close", (code) => {
          if (code !== 0) {
            reject(new Error(`ffmpeg exited with code ${code} (frames=${this._frameCount})`));
          } else {
            resolve();
          }
        });
      });
    });

    await this.cdpSession!.detach();
  }

  get frameCount(): number {
    return this._frameCount;
  }
}
