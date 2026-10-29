import { describe, it, expect } from "vitest";
import { mkdtempSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import type { Page } from "playwright";
import { createPresenter, DEFAULT_LABELS, type PresenterLabels, type PresenterOptions } from "../src/index.js";

interface Signals {
  adv?: boolean;
  lang?: boolean;
}

interface Paint {
  kind: "bar" | "failBar" | "card";
  arg: { message?: string; caption?: string; labels: PresenterLabels };
}

// A page that records what the presenter paints and answers its polls: the bar's signals
// from `signals` in turn (then "advance"), the failure bar's choice with "skip".
function makeFakePage(signals: Signals[] = []): { page: Page; paints: Paint[] } {
  const paints: Paint[] = [];
  const page = {
    on() {},
    url: () => "about:blank",
    async waitForTimeout() {},
    async evaluate(fn: (...args: unknown[]) => unknown, arg?: unknown) {
      const source = fn.toString();
      if (typeof arg === "string") return true;
      if (source.includes("__pRetry ?")) return "skip";
      if (source.includes("goto:")) {
        const next = signals.shift() ?? { adv: true };
        return { adv: false, lang: false, play: false, pause: false, goto: null, restart: false, ...next };
      }
      if (arg && typeof arg === "object" && "labels" in arg) {
        const kind = "retrying" in arg ? "failBar" : "caption" in arg ? "bar" : "card";
        paints.push({ kind, arg: arg as Paint["arg"] });
      }
      return undefined;
    },
  };
  return { page: page as unknown as Page, paints };
}

function options(extra: PresenterOptions = {}): PresenterOptions {
  return { signalPrefix: join(mkdtempSync(join(tmpdir(), "presenter-test-")), "signal"), ...extra };
}

function last(paints: Paint[], kind: Paint["kind"]): Paint["arg"] {
  const found = paints.filter((p) => p.kind === kind).at(-1);
  if (!found) throw new Error(`no ${kind} was painted`);
  return found.arg;
}

const failure = { en: "the menu shows no EUR", de: "das Menü zeigt kein EUR" };

describe("presenter", () => {
  it("paints the failure bar in the language the EN/DE button selected", async () => {
    const { page, paints } = makeFakePage([{ lang: true }, { adv: true }]);
    const presenter = await createPresenter(page, options({ lang: "en" }));
    await presenter.beat({ en: "Open the menu", de: "Menü öffnen" });

    expect(await presenter.beatFailed(failure)).toBe("skip");

    const bar = last(paints, "failBar");
    expect(bar.message).toBe(failure.de);
    expect(bar.labels).toEqual(DEFAULT_LABELS.de);
  });

  it("paints the retrying bar in the current language", async () => {
    const { page, paints } = makeFakePage();
    const presenter = await createPresenter(page, options({ lang: "de" }));

    await presenter.beatRetrying(failure);

    const bar = last(paints, "failBar");
    expect(bar.message).toBe(failure.de);
    expect(bar.labels.retrying).toBe(DEFAULT_LABELS.de.retrying);
  });

  it("shows a plain failure text as it is", async () => {
    const { page, paints } = makeFakePage();
    const presenter = await createPresenter(page, options());

    await presenter.beatFailed("boom");

    const bar = last(paints, "failBar");
    expect(bar.message).toBe("boom");
    expect(bar.labels).toEqual(DEFAULT_LABELS.en);
  });

  it("switches the bar's and the title card's labels with the language", async () => {
    const { page, paints } = makeFakePage([{ lang: true }, { adv: true }]);
    const presenter = await createPresenter(page, options({ lang: "de" }));

    await presenter.title({ en: "Demo", de: "Vorführung" });

    const cards = paints.filter((p) => p.kind === "card").map((p) => p.arg.labels);
    expect(cards[0]).toEqual(DEFAULT_LABELS.de);
    expect(cards.at(-1)).toEqual(DEFAULT_LABELS.en);

    await presenter.beat("x");
    expect(last(paints, "bar").labels).toEqual(DEFAULT_LABELS.en);
  });

  it("takes the caller's labels over the defaults, per language", async () => {
    const { page, paints } = makeFakePage();
    const presenter = await createPresenter(page, options({ lang: "de", labels: { de: { next: "▶ Los" } } }));

    await presenter.beat("x");

    expect(last(paints, "bar").labels).toEqual({ ...DEFAULT_LABELS.de, next: "▶ Los" });
  });

  it("offers every label in both languages", () => {
    expect(Object.keys(DEFAULT_LABELS.de).sort()).toEqual(Object.keys(DEFAULT_LABELS.en).sort());
    for (const lang of ["en", "de"] as const) {
      for (const text of Object.values(DEFAULT_LABELS[lang])) expect(text.trim()).not.toBe("");
    }
  });
});
