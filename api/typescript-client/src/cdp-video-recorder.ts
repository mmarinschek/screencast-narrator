import { CDPSession, Page } from "playwright";
import { spawn, ChildProcess } from "child_process";
import { mkdirSync } from "fs";
import { dirname } from "path";
import { SharedConfig } from "./index.js";

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

    this.cdpSession.on("Page.screencastFrame", (event) => {
      if (!this.recording) return;
      const data: string = event.data;
      const sessionId: number = event.sessionId;
      const frameBytes = Buffer.from(data, "base64");
      if (this.ffmpegProcess?.stdin?.writable) {
        this.ffmpegProcess.stdin.write(frameBytes);
      }
      this._frameCount++;
      this.cdpSession!.send("Page.screencastFrameAck", { sessionId });
    });

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
    const maxWaits = 50;
    for (let i = 0; i < maxWaits && this._frameCount < rec.minFrames; i++) {
      await this.page.waitForTimeout(rec.minFrameWaitMs);
    }
    if (this._frameCount < 1) {
      throw new Error(`CDP screencast: no frames received after ${maxWaits * rec.minFrameWaitMs}ms`);
    }
  }

  async stop(): Promise<void> {
    if (!this.recording) return;
    const rec = this.config.recording;

    if (this._frameCount < rec.minFrames) {
      const waits = (rec.minFrames - this._frameCount) * 2;
      for (let i = 0; i < waits && this._frameCount < rec.minFrames; i++) {
        await this.page.waitForTimeout(rec.minFrameWaitMs);
      }
    }

    this.recording = false;
    await this.cdpSession!.send("Page.stopScreencast");
    await this.page.waitForTimeout(rec.stopSettleMs);

    await new Promise<void>((resolve, reject) => {
      if (!this.ffmpegProcess?.stdin) {
        resolve();
        return;
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
