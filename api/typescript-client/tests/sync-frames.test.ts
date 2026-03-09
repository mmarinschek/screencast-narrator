import { describe, it, expect } from "vitest";
import {
  loadSharedConfig,
  formatInitData,
  formatSyncData,
  splitIntoContinuationFrames,
} from "../src/index.js";

const config = loadSharedConfig();
const sm = config.syncMarkers;

describe("sync frame payloads", () => {
  it("includes vc field when voice is provided", () => {
    const payload = formatSyncData(sm, 0, sm.start, "Hello", undefined, "douglas");
    const parsed = JSON.parse(payload);

    expect(parsed.tx).toBe("Hello");
    expect(parsed.vc).toBe("douglas");
  });

  it("omits vc field when voice is not provided", () => {
    const payload = formatSyncData(sm, 0, sm.start, "Hello");
    const parsed = JSON.parse(payload);

    expect(parsed.tx).toBe("Hello");
    expect(parsed.vc).toBeUndefined();
  });

  it("includes voices field in init frame when provided", () => {
    const voices = { douglas: { en: "am_adam" }, natalie: { en: "bf_alice" } };
    const payload = formatInitData(sm, "en", false, 24, voices);
    const parsed = JSON.parse(payload);

    expect(parsed.voices.douglas.en).toBe("am_adam");
    expect(parsed.voices.natalie.en).toBe("bf_alice");
  });

  it("omits voices field in init frame when not provided", () => {
    const payload = formatInitData(sm, "en");
    const parsed = JSON.parse(payload);

    expect(parsed.voices).toBeUndefined();
  });

  it("includes translations and voice together", () => {
    const payload = formatSyncData(sm, 0, sm.start, "Hello", { de: "Hallo" }, "harmony");
    const parsed = JSON.parse(payload);

    expect(parsed.tx).toBe("Hello");
    expect(parsed.tr.de).toBe("Hallo");
    expect(parsed.vc).toBe("harmony");
  });

  it("returns single frame for small payload", () => {
    const payload = formatSyncData(sm, 0, sm.start, "short", undefined, "douglas");
    const frames = splitIntoContinuationFrames(payload);

    expect(frames).toHaveLength(1);
    expect(frames[0]).toBe(payload);
  });
});
