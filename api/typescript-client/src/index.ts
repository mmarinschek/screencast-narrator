import { Locator, Page } from "playwright";
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { HighlightStyle } from "./generated/storyboard-types.js";
import { ConfigSchema, RecordingConfig, HighlightConfig } from "./generated/config-types.js";
import { CdpVideoRecorder } from "./cdp-video-recorder.js";

const __dir = dirname(fileURLToPath(import.meta.url));
const configPath = resolve(__dir, "../../common/config.json");

export { HighlightStyle } from "./generated/storyboard-types.js";
export { RecordingConfig, HighlightConfig } from "./generated/config-types.js";

function mergeHighlightStyles(base: HighlightStyle, override: HighlightStyle): HighlightStyle {
  return {
    color: override.color ?? base.color,
    animationSpeedMs: override.animationSpeedMs ?? base.animationSpeedMs,
    drawDurationMs: override.drawDurationMs ?? base.drawDurationMs,
    opacity: override.opacity ?? base.opacity,
    padding: override.padding ?? base.padding,
    scrollWaitMs: override.scrollWaitMs ?? base.scrollWaitMs,
    removeWaitMs: override.removeWaitMs ?? base.removeWaitMs,
    lineWidthMin: override.lineWidthMin ?? base.lineWidthMin,
    lineWidthMax: override.lineWidthMax ?? base.lineWidthMax,
    segments: override.segments ?? base.segments,
    coverage: override.coverage ?? base.coverage,
  };
}

export class SharedConfig {
  readonly recording: RecordingConfig;
  readonly highlight: HighlightConfig;
  private readonly configDir: string;

  constructor(recording: RecordingConfig, highlight: HighlightConfig, configDir: string) {
    this.recording = recording;
    this.highlight = highlight;
    this.configDir = configDir;
  }

  get resolvedScrollJs(): string {
    return this.resolveJs(this.highlight.scrollJs);
  }

  get resolvedScrollWaitJs(): string {
    return this.resolveJs(this.highlight.scrollWaitJs);
  }

  get resolvedDrawJs(): string {
    let result = this.resolveJs(this.highlight.drawJs);
    for (const [key, value] of Object.entries(this.highlight)) {
      result = result.replaceAll(`{{${key}}}`, String(value));
    }
    return result;
  }

  get resolvedRemoveJs(): string {
    return this.resolveJs(this.highlight.removeJs);
  }

  ffmpegArgs(outputFile: string): string[] {
    const rec = this.recording;
    return [
      "ffmpeg",
      "-loglevel", "error",
      "-f", "image2pipe",
      "-avioflags", "direct",
      "-fpsprobesize", "0",
      "-probesize", "32",
      "-analyzeduration", "0",
      "-c:v", "mjpeg",
      "-i", "pipe:0",
      "-y", "-an",
      "-r", String(rec.fps),
      "-c:v", rec.codec,
      "-preset", rec.preset,
      "-crf", String(rec.crf),
      "-pix_fmt", rec.pixelFormat,
      "-threads", "1",
      outputFile,
    ];
  }

  withHighlightOverrides(style: HighlightStyle): SharedConfig {
    const hl = this.highlight;
    const overridden: HighlightConfig = {
      ...hl,
      scrollWaitMs: style.scrollWaitMs ?? hl.scrollWaitMs,
      drawWaitMs: style.drawDurationMs ?? hl.drawWaitMs,
      removeWaitMs: style.removeWaitMs ?? hl.removeWaitMs,
      color: style.color ?? hl.color,
      padding: style.padding ?? hl.padding,
      animationSpeedMs: style.animationSpeedMs ?? hl.animationSpeedMs,
      lineWidthMin: style.lineWidthMin ?? hl.lineWidthMin,
      lineWidthMax: style.lineWidthMax ?? hl.lineWidthMax,
      opacity: style.opacity ?? hl.opacity,
      segments: style.segments ?? hl.segments,
      coverage: style.coverage ?? hl.coverage,
    };
    return new SharedConfig(this.recording, overridden, this.configDir);
  }

  private resolveJs(value: string): string {
    if (!value.endsWith(".js")) return value;
    const jsPath = resolve(this.configDir, value);
    try {
      return readFileSync(jsPath, "utf-8").trim();
    } catch {
      return value;
    }
  }
}

export function loadSharedConfig(): SharedConfig {
  const raw = JSON.parse(readFileSync(configPath, "utf-8")) as ConfigSchema;
  const configDir = dirname(configPath);
  return new SharedConfig(raw.recording, raw.highlight, configDir);
}

export type ScreenActionTiming = "casted" | "elastic" | "timed";

interface ScreenActionEntry {
  screenActionId: number;
  description?: string;
  timing?: "elastic" | "timed";
  durationMs?: number;
}

interface HighlightEntry {
  highlightId: number;
}

interface NarrationEntry {
  narrationId: number;
  text?: string;
  voice?: string;
  translations?: Record<string, string>;
  screenActions?: ScreenActionEntry[];
  highlights?: HighlightEntry[];
  videoFile?: string;
}

export class Storyboard {
  private readonly config: SharedConfig;
  private readonly outputDir: string;
  private readonly page: Page | null;
  private readonly language: string;
  private readonly videoWidth: number;
  private readonly videoHeight: number;
  private readonly narrations: NarrationEntry[] = [];
  private narrationIdCounter = 0;
  private screenActionIdCounter = 0;
  private highlightIdCounter = 0;
  private narrationOpen = false;
  private pendingText: string | null = null;
  private pendingTranslations: Record<string, string> = {};
  private pendingNarrationId = -1;
  private pendingScreenActions: ScreenActionEntry[] = [];
  private pendingHighlights: HighlightEntry[] = [];
  private pendingVoice: string | undefined = undefined;
  private pendingActionId: number | null = null;
  private _highlightStyle: HighlightStyle;
  private _debugOverlay: boolean;
  private _fontSize: number;
  private _voices: Record<string, Record<string, string>> | undefined;
  private currentRecorder: CdpVideoRecorder | null = null;
  private narrationStartTimeMs = 0;

  constructor(outputDir: string, page?: Page, options?: {
    language?: string;
    highlightStyle?: HighlightStyle;
    debugOverlay?: boolean;
    fontSize?: number;
    voices?: Record<string, Record<string, string>>;
    videoWidth?: number;
    videoHeight?: number;
  }) {
    this.config = loadSharedConfig();
    this.outputDir = outputDir;
    this.page = page ?? null;
    this.language = options?.language ?? "en";
    this._highlightStyle = options?.highlightStyle ?? {};
    this._debugOverlay = options?.debugOverlay ?? false;
    this._fontSize = options?.fontSize ?? 24;
    this._voices = options?.voices;
    this.videoWidth = options?.videoWidth ?? 1280;
    this.videoHeight = options?.videoHeight ?? 720;
    mkdirSync(outputDir, { recursive: true });
  }

  get highlightStyle(): HighlightStyle {
    return this._highlightStyle;
  }

  withHighlightStyle(style: HighlightStyle): this {
    this._highlightStyle = mergeHighlightStyles(this._highlightStyle, style);
    return this;
  }

  private get debugOverlay(): boolean {
    return this._debugOverlay;
  }

  private get fontSize(): number {
    return this._fontSize;
  }

  private elapsedMs(): number {
    return performance.now() - this.narrationStartTimeMs;
  }

  private async startRecording(narrationId: number): Promise<void> {
    const videoFile = join(this.outputDir, "videos", `narration-${String(narrationId).padStart(3, "0")}.mp4`);
    this.currentRecorder = new CdpVideoRecorder(this.page!, videoFile, this.videoWidth, this.videoHeight, this.config);
    await this.currentRecorder.start();
    this.narrationStartTimeMs = performance.now();
  }

  private async stopRecording(): Promise<void> {
    if (!this.currentRecorder) return;
    await this.currentRecorder.stop();
    this.currentRecorder = null;
  }

  async beginNarration(text?: string, translations?: Record<string, string>, voice?: string): Promise<number> {
    if (this.narrationOpen) {
      throw new Error("Cannot begin a new narration while another is still open");
    }
    const nid = this.narrationIdCounter++;
    this.narrationOpen = true;
    this.pendingNarrationId = nid;
    this.pendingText = text ?? null;
    this.pendingVoice = voice;
    this.pendingTranslations = translations ? { ...translations } : {};
    this.pendingScreenActions = [];
    this.pendingHighlights = [];
    if (this.page) {
      await this.startRecording(nid);
    }
    return nid;
  }

  async beginScreenAction(options?: {
    description?: string;
    timing?: ScreenActionTiming;
    durationMs?: number;
  }): Promise<number> {
    if (!this.narrationOpen) {
      throw new Error("Cannot begin a screen action outside of a narration bracket");
    }
    if (this.pendingActionId !== null) {
      throw new Error("Cannot begin a new screen action while another is still open");
    }
    const timing = options?.timing ?? "casted";
    if (timing === "timed" && options?.durationMs === undefined) {
      throw new Error("durationMs is required when timing is 'timed'");
    }
    const said = this.screenActionIdCounter++;
    const action: ScreenActionEntry = { screenActionId: said };
    if (options?.description !== undefined) {
      action.description = options.description;
    }
    if (timing !== "casted") {
      action.timing = timing;
    }
    if (options?.durationMs !== undefined) {
      action.durationMs = options.durationMs;
    }
    this.pendingScreenActions.push(action);
    this.pendingActionId = said;
    return said;
  }

  async highlight(locator: Locator): Promise<void> {
    if (!this.page) {
      throw new Error("Cannot highlight: no page was provided to Storyboard");
    }
    if (!this.narrationOpen) {
      throw new Error("Cannot highlight outside of a narration bracket");
    }
    const hid = this.highlightIdCounter++;
    await this.highlightElement(locator);
    this.pendingHighlights.push({ highlightId: hid });
  }

  async endScreenAction(): Promise<void> {
    if (this.pendingActionId === null) {
      throw new Error("Cannot end screen action: no screen action is open");
    }
    this.pendingActionId = null;
  }

  async narrate(callback: (sb: Storyboard) => Promise<void>, text?: string, translations?: Record<string, string>, voice?: string): Promise<number> {
    const nid = await this.beginNarration(text, translations, voice);
    try {
      await callback(this);
    } finally {
      if (this.pendingActionId !== null) {
        await this.endScreenAction();
      }
      await this.endNarration();
    }
    return nid;
  }

  async screenAction(callback: (sb: Storyboard) => Promise<void>, options?: {
    description?: string;
    timing?: ScreenActionTiming;
    durationMs?: number;
  }): Promise<number> {
    const said = await this.beginScreenAction(options);
    try {
      await callback(this);
    } finally {
      await this.endScreenAction();
    }
    return said;
  }

  async done(): Promise<void> {
    if (this.narrationOpen) {
      throw new Error("Cannot finalize: a narration bracket is still open");
    }
    this.flush();
  }

  async endNarration(): Promise<void> {
    if (!this.narrationOpen) {
      throw new Error("Cannot end narration: no narration bracket is open");
    }
    if (this.pendingActionId !== null) {
      throw new Error("Cannot end narration while a screen action is still open");
    }
    await this.stopRecording();
    const narration: NarrationEntry = {
      narrationId: this.pendingNarrationId,
    };
    if (this.pendingText !== null) {
      narration.text = this.pendingText;
    }
    if (this.pendingVoice !== undefined) {
      narration.voice = this.pendingVoice;
    }
    if (Object.keys(this.pendingTranslations).length > 0) {
      narration.translations = { ...this.pendingTranslations };
    }
    narration.videoFile = `videos/narration-${String(this.pendingNarrationId).padStart(3, "0")}.mp4`;
    if (this.pendingScreenActions.length > 0) {
      narration.screenActions = [...this.pendingScreenActions];
    }
    if (this.pendingHighlights.length > 0) {
      narration.highlights = [...this.pendingHighlights];
    }
    this.narrations.push(narration);
    this.narrationOpen = false;
    this.pendingText = null;
    this.pendingVoice = undefined;
    this.pendingTranslations = {};
    this.pendingNarrationId = -1;
    this.pendingScreenActions = [];
    this.pendingHighlights = [];
    this.flush();
  }

  private flush(): void {
    const data: Record<string, unknown> = {
      language: this.language,
      narrations: this.narrations,
    };
    const options: Record<string, unknown> = {};
    if (Object.keys(this._highlightStyle).length > 0) options.highlightStyle = this._highlightStyle;
    if (this._voices) options.voices = this._voices;
    if (this.debugOverlay) options.debugOverlay = true;
    if (this.fontSize !== 24) options.fontSize = this.fontSize;
    if (Object.keys(options).length > 0) data.options = options;
    writeFileSync(
      join(this.outputDir, "storyboard.json"),
      JSON.stringify(data, null, 2)
    );
  }

  private async highlightElement(locator: Locator): Promise<void> {
    if (!this.page) return;
    const hlConfig = this.config.withHighlightOverrides(this._highlightStyle);
    await locator.evaluate((el, code) => new Function("return " + code)()(el), hlConfig.resolvedScrollJs);
    await this.page.evaluate((code) => new Function("return " + code)()(), hlConfig.resolvedScrollWaitJs);
    await locator.evaluate((el, code) => new Function("return " + code)()(el), hlConfig.resolvedDrawJs);
    await this.page.waitForTimeout(hlConfig.highlight.animationSpeedMs + hlConfig.highlight.drawWaitMs);
    await this.page.evaluate(hlConfig.resolvedRemoveJs);
    await this.page.waitForTimeout(hlConfig.highlight.removeWaitMs);
  }
}
