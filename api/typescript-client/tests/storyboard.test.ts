import { describe, it, expect } from "vitest";
import { mkdtempSync, readFileSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { Storyboard } from "../src/index.js";

function makeTmpDir(): string {
  return mkdtempSync(join(tmpdir(), "storyboard-test-"));
}

describe("storyboard", () => {
  it("creates narration entry with text", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("Hello world");
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.narrations).toHaveLength(1);
    expect(data.narrations[0].narrationId).toBe(0);
    expect(data.narrations[0].text).toBe("Hello world");
  });

  it("auto-increments narration IDs", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("First");
    await sb.endNarration();
    await sb.beginNarration("Second");
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.narrations[0].narrationId).toBe(0);
    expect(data.narrations[1].narrationId).toBe(1);
  });

  it("stores voice on narration", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir, undefined, { voices: { douglas: { en: "am_adam" } } });
    await sb.beginNarration("Hello", undefined, "douglas");
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.narrations[0].voice).toBe("douglas");
  });

  it("omits voice when not specified", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("Hello");
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.narrations[0].voice).toBeUndefined();
  });

  it("stores translations on narration", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("Hello", { de: "Hallo" });
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.narrations[0].translations.de).toBe("Hallo");
  });

  it("includes videoFile path on narration", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("Hello");
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.narrations[0].videoFile).toBe("videos/narration-000.mp4");
  });

  it("includes voices in options", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir, undefined, {
      voices: { douglas: { en: "am_adam" }, natalie: { en: "bf_alice" } },
    });
    await sb.beginNarration("Hello", undefined, "douglas");
    await sb.endNarration();

    const data = JSON.parse(readFileSync(join(dir, "storyboard.json"), "utf-8"));
    expect(data.options.voices.douglas.en).toBe("am_adam");
    expect(data.options.voices.natalie.en).toBe("bf_alice");
  });

  it("throws when nested narrations", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("First");
    await expect(sb.beginNarration("Second")).rejects.toThrow(
      "Cannot begin a new narration while another is still open"
    );
  });

  it("done succeeds after all narrations closed", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("Hello");
    await sb.endNarration();
    await expect(sb.done()).resolves.toBeUndefined();
  });

  it("done throws if narration is open", async () => {
    const dir = makeTmpDir();
    const sb = new Storyboard(dir);
    await sb.beginNarration("Hello");
    await expect(sb.done()).rejects.toThrow("Cannot finalize: a narration bracket is still open");
  });
});
