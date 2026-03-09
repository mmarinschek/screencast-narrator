import { Locator, Page } from "playwright";
import QRCode from "qrcode";
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { HighlightStyle, SyncFrameStyle } from "./generated/storyboard-types.js";

const __dir = dirname(fileURLToPath(import.meta.url));
const configPath = resolve(__dir, "../../common/config.json");

export enum SyncType {
  INIT = "init",
  NARRATION = "nar",
  ACTION = "act",
  HIGHLIGHT = "hlt",
  DONE = "done",
}

export enum MarkerPosition {
  START = "start",
  END = "end",
}

interface SyncMarkersConfig {
  init: SyncType;
  narration: SyncType;
  action: SyncType;
  highlight: SyncType;
  done: SyncType;
  separator: string;
  start: MarkerPosition;
  end: MarkerPosition;
}

interface SyncFrameConfig {
  qrSize: number;
  displayDurationMs: number;
  doneDisplayDurationMs: number;
  postRemovalGapMs: number;
  backgroundColor: string;
  injectJs: string;
  removeJs: string;
}

interface HighlightConfig {
  scrollWaitMs: number;
  drawWaitMs: number;
  removeWaitMs: number;
  color: string;
  padding: number;
  animationSpeedMs: number;
  lineWidthMin: number;
  lineWidthMax: number;
  opacity: number;
  segments: number;
  coverage: number;
  scrollJs: string;
  scrollWaitJs: string;
  drawJs: string;
  removeJs: string;
}

export interface SharedConfig {
  syncMarkers: SyncMarkersConfig;
  syncFrame: SyncFrameConfig;
  highlight: HighlightConfig;
}

export { HighlightStyle, SyncFrameStyle } from "./generated/storyboard-types.js";

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

function mergeSyncFrameStyles(base: SyncFrameStyle, override: SyncFrameStyle): SyncFrameStyle {
  return {
    displayDurationMs: override.displayDurationMs ?? base.displayDurationMs,
    postRemovalGapMs: override.postRemovalGapMs ?? base.postRemovalGapMs,
    debugOverlay: override.debugOverlay ?? base.debugOverlay,
    fontSize: override.fontSize ?? base.fontSize,
  };
}

function applyHighlightStyle(style: HighlightStyle, config: HighlightConfig): HighlightConfig {
  return {
    ...config,
    color: style.color ?? config.color,
    padding: style.padding ?? config.padding,
    animationSpeedMs: style.animationSpeedMs ?? config.animationSpeedMs,
    drawWaitMs: style.drawDurationMs ?? config.drawWaitMs,
    opacity: style.opacity ?? config.opacity,
    scrollWaitMs: style.scrollWaitMs ?? config.scrollWaitMs,
    removeWaitMs: style.removeWaitMs ?? config.removeWaitMs,
    lineWidthMin: style.lineWidthMin ?? config.lineWidthMin,
    lineWidthMax: style.lineWidthMax ?? config.lineWidthMax,
    segments: style.segments ?? config.segments,
    coverage: style.coverage ?? config.coverage,
  };
}

function resolveJs(configDir: string, value: string): string {
  if (!value.endsWith(".js")) return value;
  const jsPath = resolve(configDir, value);
  try {
    return readFileSync(jsPath, "utf-8").trim();
  } catch {
    return value;
  }
}

export function loadSharedConfig(): SharedConfig {
  const raw = JSON.parse(readFileSync(configPath, "utf-8"));
  const configDir = dirname(configPath);
  raw.syncFrame.injectJs = resolveJs(configDir, raw.syncFrame.injectJs);
  raw.syncFrame.removeJs = resolveJs(configDir, raw.syncFrame.removeJs);
  raw.highlight.scrollJs = resolveJs(configDir, raw.highlight.scrollJs);
  raw.highlight.scrollWaitJs = resolveJs(configDir, raw.highlight.scrollWaitJs);
  raw.highlight.drawJs = resolveJs(configDir, raw.highlight.drawJs);
  raw.highlight.removeJs = resolveJs(configDir, raw.highlight.removeJs);
  return raw;
}

function resolveDrawJs(cfg: HighlightConfig): string {
  return cfg.drawJs
    .replace(/\{\{padding\}\}/g, String(cfg.padding))
    .replace(/\{\{lineWidthMin\}\}/g, String(cfg.lineWidthMin))
    .replace(/\{\{lineWidthMax\}\}/g, String(cfg.lineWidthMax))
    .replace(/\{\{opacity\}\}/g, String(cfg.opacity))
    .replace(/\{\{segments\}\}/g, String(cfg.segments))
    .replace(/\{\{coverage\}\}/g, String(cfg.coverage))
    .replace(/\{\{animationSpeedMs\}\}/g, String(cfg.animationSpeedMs))
    .replace(/\{\{color\}\}/g, cfg.color);
}

export function formatInitData(syncMarkers: SyncMarkersConfig, language: string, debugOverlay = false, fontSize = 24, voices?: Record<string, Record<string, string>>): string {
  const payload: Record<string, unknown> = { t: syncMarkers.init, language };
  if (debugOverlay) payload.debugOverlay = true;
  if (fontSize !== 24) payload.fontSize = fontSize;
  if (voices && Object.keys(voices).length > 0) payload.voices = voices;
  return JSON.stringify(payload);
}

export function formatSyncData(syncMarkers: SyncMarkersConfig, narrationId: number, marker: string, text = "", translations?: Record<string, string>, voice?: string): string {
  const payload: Record<string, unknown> = { t: syncMarkers.narration, id: narrationId, m: marker };
  if (text) payload.tx = text;
  if (translations && Object.keys(translations).length > 0) payload.tr = translations;
  if (voice) payload.vc = voice;
  return JSON.stringify(payload);
}

function formatActionSyncData(syncMarkers: SyncMarkersConfig, actionId: number, marker: string, options?: { description?: string; timing?: string; durationMs?: number }): string {
  const payload: Record<string, unknown> = { t: syncMarkers.action, id: actionId, m: marker };
  if (options?.description !== undefined) payload.desc = options.description;
  if (options?.timing && options.timing !== "casted") payload.tm = options.timing;
  if (options?.durationMs !== undefined) payload.dur = options.durationMs;
  return JSON.stringify(payload);
}

function formatHighlightSyncData(syncMarkers: SyncMarkersConfig, highlightId: number, marker: string): string {
  return JSON.stringify({ t: syncMarkers.highlight, id: highlightId, m: marker });
}

const MAX_QR_DATA_LENGTH = 2000;

export function splitIntoContinuationFrames(data: string): string[] {
  if (data.length <= MAX_QR_DATA_LENGTH) return [data];
  const overhead = 30;
  let chunkSize = MAX_QR_DATA_LENGTH - overhead;
  for (let attempt = 0; attempt < 20; attempt++) {
    const total = Math.ceil(data.length / chunkSize);
    const testChunk = data.substring(0, chunkSize);
    const wrapper = JSON.stringify({ _c: [0, total], d: testChunk });
    if (wrapper.length <= MAX_QR_DATA_LENGTH) break;
    chunkSize -= 50;
  }
  const total = Math.ceil(data.length / chunkSize);
  const frames: string[] = [];
  for (let i = 0; i < total; i++) {
    const chunk = data.substring(i * chunkSize, (i + 1) * chunkSize);
    frames.push(JSON.stringify({ _c: [i, total], d: chunk }));
  }
  return frames;
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
}

export class Storyboard {
  private readonly config: SharedConfig;
  private readonly outputDir: string;
  private readonly page: Page | null;
  private readonly language: string;
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
  private _syncFrameStyle: SyncFrameStyle;
  private _voices: Record<string, Record<string, string>> | undefined;

  constructor(outputDir: string, page?: Page, options?: { language?: string; highlightStyle?: HighlightStyle; syncFrameStyle?: SyncFrameStyle; voices?: Record<string, Record<string, string>> }) {
    this.config = loadSharedConfig();
    this.outputDir = outputDir;
    this.page = page ?? null;
    this.language = options?.language ?? "en";
    this._highlightStyle = options?.highlightStyle ?? {};
    this._syncFrameStyle = options?.syncFrameStyle ?? {};
    this._voices = options?.voices;
    mkdirSync(outputDir, { recursive: true });
  }

  get highlightStyle(): HighlightStyle {
    return this._highlightStyle;
  }

  withHighlightStyle(style: HighlightStyle): this {
    this._highlightStyle = mergeHighlightStyles(this._highlightStyle, style);
    return this;
  }

  get syncFrameStyle(): SyncFrameStyle {
    return this._syncFrameStyle;
  }

  withSyncFrameStyle(style: SyncFrameStyle): this {
    this._syncFrameStyle = mergeSyncFrameStyles(this._syncFrameStyle, style);
    return this;
  }

  async init(): Promise<void> {
    if (!this.page) return;
    const debugOverlay = this._syncFrameStyle.debugOverlay ?? false;
    const fontSize = this._syncFrameStyle.fontSize ?? 24;
    await this.injectQrOverlay(formatInitData(this.config.syncMarkers, this.language, debugOverlay, fontSize, this._voices));
  }

  async beginNarration(text?: string, translations?: Record<string, string>, voice?: string): Promise<number> {
    if (this.narrationOpen) {
      throw new Error(
        "Cannot begin a new narration while another is still open"
      );
    }
    const nid = this.narrationIdCounter++;
    this.narrationOpen = true;
    this.pendingNarrationId = nid;
    this.pendingText = text ?? null;
    this.pendingVoice = voice;
    this.pendingTranslations = translations ? { ...translations } : {};
    this.pendingScreenActions = [];
    this.pendingHighlights = [];
    const tr = Object.keys(this.pendingTranslations).length > 0 ? this.pendingTranslations : undefined;
    await this.injectSyncFrame(nid, this.config.syncMarkers.start, text ?? "", tr, voice);
    return nid;
  }

  async beginScreenAction(options?: {
    description?: string;
    timing?: ScreenActionTiming;
    durationMs?: number;
  }): Promise<number> {
    if (!this.narrationOpen) {
      throw new Error(
        "Cannot begin a screen action outside of a narration bracket"
      );
    }
    if (this.pendingActionId !== null) {
      throw new Error(
        "Cannot begin a new screen action while another is still open"
      );
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
    await this.injectActionSyncFrame(said, this.config.syncMarkers.start, {
      description: options?.description,
      timing: timing !== "casted" ? timing : undefined,
      durationMs: options?.durationMs,
    });
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
    await this.injectHighlightSyncFrame(hid, this.config.syncMarkers.start);
    await this.highlightElement(locator);
    await this.injectHighlightSyncFrame(hid, this.config.syncMarkers.end);
    this.pendingHighlights.push({ highlightId: hid });
  }

  async endScreenAction(): Promise<void> {
    if (this.pendingActionId === null) {
      throw new Error("Cannot end screen action: no screen action is open");
    }
    await this.injectActionSyncFrame(this.pendingActionId, this.config.syncMarkers.end);
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
    if (!this.page) return;
    const savedDisplay = this._syncFrameStyle.displayDurationMs;
    this._syncFrameStyle.displayDurationMs = this.config.syncFrame.doneDisplayDurationMs;
    await this.injectQrOverlay(JSON.stringify({ t: this.config.syncMarkers.done }));
    this._syncFrameStyle.displayDurationMs = savedDisplay;
  }

  async endNarration(): Promise<void> {
    if (!this.narrationOpen) {
      throw new Error("Cannot end narration: no narration bracket is open");
    }
    if (this.pendingActionId !== null) {
      throw new Error(
        "Cannot end narration while a screen action is still open"
      );
    }
    await this.injectSyncFrame(this.pendingNarrationId, this.config.syncMarkers.end);
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
    if (Object.keys(this._syncFrameStyle).length > 0) options.syncFrameStyle = this._syncFrameStyle;
    if (this._voices) options.voices = this._voices;
    if (Object.keys(options).length > 0) data.options = options;
    writeFileSync(
      join(this.outputDir, "storyboard.json"),
      JSON.stringify(data, null, 2)
    );
  }

  private async highlightElement(locator: Locator): Promise<void> {
    if (!this.page) return;
    const hlConfig = applyHighlightStyle(this._highlightStyle, this.config.highlight);
    const resolved = resolveDrawJs(hlConfig);
    await locator.evaluate((el, code) => new Function("return " + code)()(el), hlConfig.scrollJs);
    await this.page.evaluate((code) => new Function("return " + code)()(), hlConfig.scrollWaitJs);
    await locator.evaluate((el, code) => new Function("return " + code)()(el), resolved);
    await this.page.waitForTimeout(hlConfig.animationSpeedMs + hlConfig.drawWaitMs);
    await this.page.evaluate(hlConfig.removeJs);
    await this.page.waitForTimeout(hlConfig.removeWaitMs);
  }

  private async injectSyncFrame(
    narrationId: number,
    marker: string,
    text: string = "",
    translations?: Record<string, string>,
    voice?: string
  ): Promise<void> {
    if (!this.page) return;
    await this.injectQrOverlay(
      formatSyncData(this.config.syncMarkers, narrationId, marker, text, translations, voice)
    );
  }

  private async injectActionSyncFrame(
    screenActionId: number,
    marker: string,
    options?: { description?: string; timing?: string; durationMs?: number }
  ): Promise<void> {
    if (!this.page) return;
    await this.injectQrOverlay(
      formatActionSyncData(this.config.syncMarkers, screenActionId, marker, options)
    );
  }

  private async injectHighlightSyncFrame(
    highlightId: number,
    marker: string
  ): Promise<void> {
    if (!this.page) return;
    await this.injectQrOverlay(
      formatHighlightSyncData(this.config.syncMarkers, highlightId, marker)
    );
  }

  private async injectQrOverlay(data: string): Promise<void> {
    if (!this.page) return;
    const frames = splitIntoContinuationFrames(data);
    for (let i = 0; i < frames.length; i++) {
      const label = i === 0 ? data : `(cont ${i + 1}/${frames.length})`;
      await this.injectSingleQr(frames[i], label);
    }
  }

  private async injectSingleQr(data: string, label: string = ""): Promise<void> {
    if (!this.page) return;
    const sfConfig = this.config.syncFrame;
    const displayDurationMs = this._syncFrameStyle.displayDurationMs ?? sfConfig.displayDurationMs;
    const postRemovalGapMs = this._syncFrameStyle.postRemovalGapMs ?? sfConfig.postRemovalGapMs;
    const dataUrl = await QRCode.toDataURL(data, {
      width: sfConfig.qrSize,
      margin: 4,
    });
    const escaped = label.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, "\\n");
    const js = sfConfig.injectJs.replace("{{backgroundColor}}", sfConfig.backgroundColor).replace("{{dataUrl}}", dataUrl).replace("{{label}}", escaped);
    await this.page.evaluate(js);
    await this.page.waitForTimeout(displayDurationMs);
    await this.page.evaluate(sfConfig.removeJs);
    await this.page.waitForTimeout(postRemovalGapMs);
  }
}
