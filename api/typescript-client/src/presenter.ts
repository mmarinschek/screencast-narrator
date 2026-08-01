import type { Page } from "playwright";
import { existsSync, rmSync } from "node:fs";

/**
 * A live presenter bar for interactive "watch mode" demo runs. Shows an on-screen
 * caption bar at the bottom of the page (NO audio, NO video) and drives a narrated
 * walk two ways:
 *
 * - **▶ Next** — advance one beat per click. Keyboard input is deliberately ignored
 *   so the presenter can type into the app during the demo without stealing focus.
 * - **▶▶ Play** — auto-advance the rest, one beat every {@link autoAdvanceMs}, with
 *   **⏸ Pause** to stop and drive by hand again.
 *
 * Captions are bilingual (`{ en, de }`); an **EN⇌DE** button toggles the language
 * live. Optional context buttons jump between apps mid-demo (e.g. an input mock and
 * the app under test), configured via {@link PresenterOptions.contexts}.
 *
 * The bar is theme-driven (see {@link PresenterTheme}) so each consuming app can
 * brand it. It has NO screencast-narrator recording dependency: it is pure Playwright
 * `page.evaluate`, driven by `window` flags the bar's buttons set, re-read on the
 * current page so it survives the hard cross-origin navigations a demo makes.
 */

export type Lang = "en" | "de";
export type Caption = string | { en: string; de: string };

export interface PresenterContext {
  label: string;
  url: string;
}

export interface PresenterTheme {
  /** Bar + title-card background. */
  barBg: string;
  /** Primary accent (Next button, step label rule, active context). */
  accent: string;
  /** Darker accent for the armed Restart state. */
  accentDark: string;
  /** Play/Pause button background. */
  playBg: string;
  /** Step label + accent text color. */
  stepColor: string;
  /** Title-card subtitle color. */
  cardSubtitle: string;
}

export interface PresenterOptions {
  /** Apps the presenter can jump between mid-walk, e.g. an input mock + the app. */
  contexts?: PresenterContext[];
  lang?: Lang;
  /** Start in auto-advance (▶▶ Play already pressed) — used by smoke runs. */
  autoPlay?: boolean;
  /** Theme overrides merged over {@link DEFAULT_THEME}. */
  theme?: Partial<PresenterTheme>;
  /** DOM id of the overlay host element. Must be unique per app. */
  overlayId?: string;
  /**
   * File-signal path prefix (default `/tmp/sn-presenter`). The test process can
   * drive the bar out-of-band by touching `<prefix>-next` / `-retry` / `-skip`,
   * which keeps working even when a tight page-reload loop kills the in-page
   * buttons. Suffixes appended: `-next`, `-retry`, `-skip`.
   */
  signalPrefix?: string;
  /** If set, a per-beat screenshot is written to `<shotDir>/beat-NN.png`. */
  shotDir?: string;
  /** Small uppercase brand label shown above the title-card headline. */
  brandLabel?: string;
  /**
   * CSS selector for a bottom-anchored fixed UI (e.g. a shadcn toast viewport)
   * that would otherwise sit behind the bar; it is lifted above the bar height.
   * Defaults to the shadcn toaster viewport selector.
   */
  toastViewportSelector?: string;
  /** Beats between auto-advance ticks in Play mode (ms). */
  autoAdvanceMs?: number;
}

export const DEFAULT_THEME: PresenterTheme = {
  barBg: "#1d3a5c",
  accent: "#e5285b",
  accentDark: "#a01d3f",
  playBg: "#3a5a7c",
  stepColor: "#f6799c",
  cardSubtitle: "#a9c2de",
};

const DEFAULT_OVERLAY_ID = "__sn_presenter";
const DEFAULT_SIGNAL_PREFIX = "/tmp/sn-presenter";
const DEFAULT_TOAST_SELECTOR = 'ol[class*="sm:bottom-0"]';
const DEFAULT_AUTO_ADVANCE_MS = 3200;
const POLL_MS = 120;

export interface Presenter {
  beat(caption: Caption, action?: () => Promise<void>): Promise<void>;
  title(title: Caption, subtitle?: Caption): Promise<void>;
  /** Show a red failure bar for a failed beat action; resolves with the presenter's choice. */
  beatFailed(message: string): Promise<"retry" | "skip">;
  /** Repaint the failure bar in a running "Retrying" state while the beat's action re-runs. */
  beatRetrying(message: string): Promise<void>;
  stop(): Promise<void>;
}

function pick(caption: Caption | undefined, lang: Lang): string {
  if (caption === undefined) return "";
  return typeof caption === "string" ? caption : caption[lang];
}

/** Thrown out of the wait loop when the presenter clicks ⟲ Restart — the spec catches it and re-runs the walk on fresh data. */
export class PresenterRestartRequested extends Error {
  constructor() {
    super("presenter requested a fresh restart");
  }
}

export async function createPresenter(page: Page, opts: PresenterOptions = {}): Promise<Presenter> {
  const contexts = opts.contexts ?? [];
  const theme: PresenterTheme = { ...DEFAULT_THEME, ...opts.theme };
  const overlayId = opts.overlayId ?? DEFAULT_OVERLAY_ID;
  const signalPrefix = opts.signalPrefix ?? DEFAULT_SIGNAL_PREFIX;
  const toastSelector = opts.toastViewportSelector ?? DEFAULT_TOAST_SELECTOR;
  const autoAdvanceMs = opts.autoAdvanceMs ?? DEFAULT_AUTO_ADVANCE_MS;
  const brandLabel = opts.brandLabel ?? "";
  const shotDir = opts.shotDir;
  let lang: Lang = opts.lang ?? "en";
  let autoPlay = opts.autoPlay ?? false;
  let step = 0;

  const fileSignals = {
    retry: `${signalPrefix}-retry`,
    skip: `${signalPrefix}-skip`,
    next: `${signalPrefix}-next`,
  } as const;

  function consumeFileSignal(kind: keyof typeof fileSignals): boolean {
    if (!existsSync(fileSignals[kind])) return false;
    rmSync(fileSignals[kind], { force: true });
    return true;
  }

  function clearFileSignals(): void {
    for (const f of Object.values(fileSignals)) rmSync(f, { force: true });
  }

  const barStyle = [
    "position:fixed;left:0;right:0;bottom:0;z-index:2147483647",
    "display:flex;align-items:center;gap:16px;padding:14px 22px",
    `background:${theme.barBg} !important;color:#fff;border-top:3px solid ${theme.accent}`,
    "opacity:1 !important;transition:none !important;animation:none !important",
    "font-family:-apple-system,'Helvetica Neue',Arial,sans-serif",
    "box-shadow:0 -6px 26px rgba(0,0,0,.30)",
    // WHY: click-transparent bar — an automated click on a page element that sits at
    // the bottom edge (scrolled minimally into view) must not be intercepted by the
    // bar; each bar button re-enables pointer-events for itself.
    "pointer-events:none",
  ].join(";");
  const cardStyle = [
    "position:fixed;inset:0;z-index:2147483647",
    "display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px",
    `background:${theme.barBg} !important;color:#fff;text-align:center;padding:64px`,
    "opacity:1 !important;transition:none !important;animation:none !important",
    "font-family:-apple-system,'Helvetica Neue',Arial,sans-serif",
  ].join(";");

  // WHY: a beat's action often starts with a navigation — the fresh document has no
  // bar, so everything the action does afterwards (e.g. typing into a form) plays
  // out with the bar missing until the post-action repaint. Re-paint the current
  // caption as soon as the new document is ready so the bar stays onscreen through
  // automatic input.
  let liveRepaint: (() => Promise<void>) | null = null;
  page.on("framenavigated", (frame) => {
    if (frame !== page.mainFrame() || !liveRepaint) return;
    void page
      .waitForLoadState("domcontentloaded")
      .then(() => liveRepaint?.())
      .catch(() => {});
  });

  function activeContextIndex(): number {
    if (!contexts.length) return -1;
    let origin = "";
    try {
      origin = new URL(page.url()).origin;
    } catch (_opaqueUrl) {
      // opaque page URL (about:blank during navigation) — no context is active
      return -1;
    }
    return contexts.findIndex((c) => {
      try {
        return new URL(c.url).origin === origin;
      } catch (_badUrl) {
        // malformed context URL — cannot be the active one
        return false;
      }
    });
  }

  async function paintBar(caption: string): Promise<void> {
    await page.evaluate(
      ({ id, style, n, caption, contexts, activeIndex, lang, playing, theme, toastSelector }) => {
        const w = window as unknown as Record<string, unknown>;
        w.__pAdv = false;
        w.__pLang = false;
        w.__pPlay = false;
        w.__pPause = false;
        w.__pGoto = null;
        w.__pRestart = false;
        w.__pRetry = false;
        w.__pSkip = false;
        const esc = (s: string) =>
          s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        const btn = (id: string, bg: string, label: string, pad = "12px 20px", extra = "") =>
          '<button id="' +
          id +
          '" style="cursor:pointer;pointer-events:auto;border:none;border-radius:9px;padding:' +
          pad +
          ";font-size:14px;font-weight:700;background:" +
          bg +
          ";color:#fff;" +
          extra +
          '">' +
          label +
          "</button>";
        const ctxHtml = contexts
          .map(
            (c: { label: string }, i: number) =>
              '<button data-pctx="' +
              i +
              '" style="cursor:pointer;pointer-events:auto;border:1px solid ' +
              (i === activeIndex ? theme.accent : "rgba(255,255,255,.28)") +
              ";border-radius:7px;padding:8px 12px;font-size:13px;font-weight:600;background:" +
              (i === activeIndex ? theme.accent : "transparent") +
              ';color:#fff">' +
              esc(c.label) +
              "</button>",
          )
          .join("");
        // WHY: the bar lives in a CLOSED shadow root — Playwright locators and the
        // walk's own full-page assertions (getByText / body toContainText) cannot
        // see into it, so caption text (which quotes the demo's names) can never
        // satisfy or break an app-level assertion while the bar persists onscreen.
        let host = document.getElementById(id);
        if (!host) {
          host = document.createElement("div");
          host.id = id;
          (host as unknown as Record<string, unknown>)._sr = host.attachShadow({ mode: "closed" });
          document.body.appendChild(host);
        }
        const root = (host as unknown as Record<string, unknown>)._sr as ShadowRoot;
        root.getElementById(id + "_card")?.remove();
        let bar = root.getElementById(id + "_bar");
        if (!bar) {
          bar = document.createElement("div");
          bar.id = id + "_bar";
          root.appendChild(bar);
        }
        bar.setAttribute("style", style);
        bar.innerHTML =
          '<span style="font:600 12px ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:' +
          theme.stepColor +
          ';white-space:nowrap">Step ' +
          n +
          "</span>" +
          '<span style="flex:1;font-size:18px;font-weight:600;line-height:1.3">' +
          esc(caption) +
          "</span>" +
          (contexts.length ? '<span style="display:flex;gap:8px">' + ctxHtml + "</span>" : "") +
          btn("__p_lang", "transparent", lang === "en" ? "DE" : "EN", "8px 12px", "border:1px solid rgba(255,255,255,.28)") +
          (playing
            ? btn("__p_pause", theme.playBg, "&#9208; Pause")
            : btn("__p_play", theme.playBg, "&#9654;&#9654; Play")) +
          btn("__p_restart", "transparent", "&#10226; Restart", "12px 14px",
              "border:1px solid rgba(255,255,255,.35);") +
          btn("__p_next", theme.accent, "&#9654; Next", "12px 24px", "font-size:15px");
        const wire = (sel: string, flag: string) => {
          const b = bar!.querySelector("#" + sel) as HTMLButtonElement | null;
          if (b) b.onclick = () => ((window as unknown as Record<string, unknown>)[flag] = true);
        };
        // WHY: the app's toast viewport is fixed at the bottom and would sit behind
        // the presenter bar — lift it (and any other bottom-anchored fixed UI
        // matching the selector) above the bar's height.
        let toastFix = document.getElementById(id + "_toastfix") as HTMLStyleElement | null;
        if (!toastFix) {
          toastFix = document.createElement("style");
          toastFix.id = id + "_toastfix";
          document.head.appendChild(toastFix);
        }
        toastFix.textContent =
          toastSelector + "{bottom:" + (bar.offsetHeight + 8) + "px !important;}";
        wire("__p_next", "__pAdv");
        wire("__p_lang", "__pLang");
        wire("__p_play", "__pPlay");
        wire("__p_pause", "__pPause");
        const restartBtn = bar.querySelector("#__p_restart") as HTMLButtonElement | null;
        if (restartBtn) {
          // WHY: no native confirm() — Playwright auto-dismisses browser dialogs, so the
          // prompt would silently cancel itself. Two-step arm instead: first click arms
          // (red, "Sure? Restart!"), second click within 4s fires; otherwise disarms.
          let armed = false;
          let disarmTimer: ReturnType<typeof setTimeout> | undefined;
          const disarm = () => {
            armed = false;
            restartBtn.innerHTML = "&#10226; Restart";
            restartBtn.style.background = "transparent";
            restartBtn.style.border = "1px solid rgba(255,255,255,.35)";
          };
          restartBtn.onclick = () => {
            if (armed) {
              if (disarmTimer !== undefined) clearTimeout(disarmTimer);
              restartBtn.innerHTML = "Restarting…";
              (window as unknown as Record<string, unknown>).__pRestart = true;
              return;
            }
            armed = true;
            restartBtn.innerHTML = "&#10226; Sure? Restart!";
            restartBtn.style.background = theme.accentDark;
            restartBtn.style.border = "1px solid " + theme.accentDark;
            disarmTimer = setTimeout(disarm, 4000);
          };
        }
        bar.querySelectorAll("[data-pctx]").forEach((b) => {
          (b as HTMLButtonElement).onclick = () =>
            ((window as unknown as Record<string, unknown>).__pGoto = (b as HTMLElement).getAttribute("data-pctx"));
        });
      },
      {
        id: overlayId,
        style: barStyle,
        n: step,
        caption,
        contexts,
        activeIndex: activeContextIndex(),
        lang,
        playing: autoPlay,
        theme,
        toastSelector,
      },
    );
  }

  async function paintFailBar(message: string, retrying = false): Promise<void> {
    await page.evaluate(
      ({ id, style, message, retrying }) => {
        const w = window as unknown as Record<string, unknown>;
        w.__pRetry = false;
        w.__pSkip = false;
        const esc = (s: string) =>
          s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        let host = document.getElementById(id);
        if (!host) {
          host = document.createElement("div");
          host.id = id;
          (host as unknown as Record<string, unknown>)._sr = host.attachShadow({ mode: "closed" });
          document.body.appendChild(host);
        }
        const root = (host as unknown as Record<string, unknown>)._sr as ShadowRoot;
        root.getElementById(id + "_card")?.remove();
        let bar = root.getElementById(id + "_bar");
        if (!bar) {
          bar = document.createElement("div");
          bar.id = id + "_bar";
          root.appendChild(bar);
        }
        bar.setAttribute("style", style);
        bar.style.setProperty("background", retrying ? "#4a3a12" : "#5c1d28", "important");
        bar.style.borderTop = retrying ? "3px solid #e0a83c" : "3px solid #ff5470";
        // WHY: the message span re-enables pointer events and user-select so the presenter
        // can copy the error text out of the otherwise click-transparent bar.
        bar.innerHTML =
          '<span style="font:600 12px ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:' +
          (retrying ? "#f0c674" : "#ff8ba0") +
          ';white-space:nowrap">' +
          (retrying ? "Retrying&#8230;" : "Beat failed") +
          "</span>" +
          '<span style="flex:1;font-size:15px;font-weight:500;line-height:1.3;pointer-events:auto;user-select:text;cursor:text;color:' +
          (retrying ? "#f5e6c8" : "#ffd9df") +
          '">' +
          esc(message) +
          "</span>" +
          (retrying
            ? ""
            : '<button id="__p_retry" style="cursor:pointer;pointer-events:auto;border:none;border-radius:9px;padding:12px 22px;font-size:14px;font-weight:700;background:#3a5a7c;color:#fff">&#10227; Retry</button>' +
              '<button id="__p_skip" style="cursor:pointer;pointer-events:auto;border:none;border-radius:9px;padding:12px 22px;font-size:14px;font-weight:700;background:#e5285b;color:#fff">&#9654; Skip &amp; continue</button>');
        const wire = (sel: string, flag: string) => {
          const b = bar!.querySelector("#" + sel) as HTMLButtonElement | null;
          if (b) b.onclick = () => ((window as unknown as Record<string, unknown>)[flag] = true);
        };
        wire("__p_retry", "__pRetry");
        wire("__p_skip", "__pSkip");
      },
      { id: overlayId, style: barStyle, message, retrying },
    );
  }

  async function paintCard(title: string, subtitle: string): Promise<void> {
    await page.evaluate(
      ({ id, style, title, subtitle, lang, theme, brandLabel }) => {
        const w = window as unknown as Record<string, unknown>;
        w.__pAdv = false;
        w.__pLang = false;
        const esc = (s: string) =>
          s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        let host = document.getElementById(id);
        if (!host) {
          host = document.createElement("div");
          host.id = id;
          (host as unknown as Record<string, unknown>)._sr = host.attachShadow({ mode: "closed" });
          document.body.appendChild(host);
        }
        const root = (host as unknown as Record<string, unknown>)._sr as ShadowRoot;
        root.getElementById(id + "_bar")?.remove();
        let card = root.getElementById(id + "_card");
        if (!card) {
          card = document.createElement("div");
          card.id = id + "_card";
          root.appendChild(card);
        }
        card.setAttribute("style", style);
        card.innerHTML =
          (brandLabel
            ? '<div style="font:600 13px ui-monospace,Menlo,monospace;letter-spacing:.24em;text-transform:uppercase;color:' +
              theme.stepColor +
              '">' +
              esc(brandLabel) +
              "</div>"
            : "") +
          '<div style="width:104px;height:2px;background:' +
          theme.accent +
          '"></div>' +
          '<h1 style="margin:0;color:#fff;font-size:52px;font-weight:700;letter-spacing:-.02em;max-width:22ch;line-height:1.06">' +
          esc(title) +
          "</h1>" +
          '<p style="margin:0;color:' +
          theme.cardSubtitle +
          ';font-size:20px;max-width:52ch;line-height:1.5">' +
          esc(subtitle) +
          "</p>" +
          '<div style="display:flex;gap:12px;margin-top:12px">' +
          '<button id="__p_lang" style="cursor:pointer;border:1px solid rgba(255,255,255,.3);border-radius:9px;padding:12px 18px;font-size:14px;font-weight:700;background:transparent;color:#fff">' +
          (lang === "en" ? "DE" : "EN") +
          "</button>" +
          '<button id="__p_next" style="cursor:pointer;border:none;border-radius:9px;padding:13px 28px;font-size:15px;font-weight:700;background:' +
          theme.accent +
          ';color:#fff">&#9654; Start</button>' +
          "</div>";
        (card.querySelector("#__p_next") as HTMLButtonElement).onclick = () =>
          ((window as unknown as Record<string, unknown>).__pAdv = true);
        (card.querySelector("#__p_lang") as HTMLButtonElement).onclick = () =>
          ((window as unknown as Record<string, unknown>).__pLang = true);
      },
      { id: overlayId, style: cardStyle, title, subtitle, lang, theme, brandLabel },
    );
  }

  async function readSignals(): Promise<{
    adv: boolean;
    lang: boolean;
    play: boolean;
    pause: boolean;
    goto: number | null;
    restart: boolean;
  }> {
    return page
      .evaluate(() => {
        const w = window as unknown as Record<string, unknown>;
        const out = {
          adv: !!w.__pAdv,
          lang: !!w.__pLang,
          play: !!w.__pPlay,
          pause: !!w.__pPause,
          goto: w.__pGoto == null ? null : Number(w.__pGoto),
          restart: !!w.__pRestart,
        };
        w.__pAdv = false;
        w.__pLang = false;
        w.__pPlay = false;
        w.__pPause = false;
        w.__pGoto = null;
        w.__pRestart = false;
        return out;
      })
      .catch(() => ({ adv: false, lang: false, play: false, pause: false, goto: null, restart: false }));
  }

  async function overlayPresent(): Promise<boolean> {
    return page
      .evaluate((id) => {
        const host = document.getElementById(id);
        const root = host && (host as unknown as Record<string, unknown>)._sr;
        return !!root && (root as ShadowRoot).childElementCount > 0;
      }, overlayId)
      .catch(() => true);
  }

  async function waitForAdvance(repaint: () => Promise<void>): Promise<void> {
    let waited = 0;
    for (;;) {
      if (consumeFileSignal("next")) return;
      // WHY: the bar lives in the page DOM — a manual navigation (the presenter clicking
      // around the app mid-demo) loads a fresh document without it, and no bar means no
      // buttons to advance with. Re-paint whenever the overlay is gone.
      if (!(await overlayPresent())) await repaint().catch(() => {});
      const s = await readSignals();
      if (s.play) {
        autoPlay = true;
        await repaint().catch(() => {});
      }
      if (s.pause) {
        autoPlay = false;
        waited = 0;
        await repaint().catch(() => {});
      }
      if (s.goto != null && contexts[s.goto]) {
        await page.goto(contexts[s.goto].url, { waitUntil: "domcontentloaded" }).catch(() => {});
        await repaint().catch(() => {});
        continue;
      }
      if (s.lang) {
        lang = lang === "en" ? "de" : "en";
        await repaint().catch(() => {});
        continue;
      }
      if (s.restart) throw new PresenterRestartRequested();
      if (s.adv) return;
      if (autoPlay) {
        waited += POLL_MS;
        if (waited >= autoAdvanceMs) return;
      }
      await page.waitForTimeout(POLL_MS);
    }
  }

  async function clearOverlay(): Promise<void> {
    await page.evaluate((id) => document.getElementById(id)?.remove(), overlayId).catch(() => {});
  }

  return {
    // WHY: act FIRST, then hold. The caption paints, the beat's action (navigation,
    // form entry, sync) runs beneath it, the caption re-asserts over the RESULT, and
    // only then does the presenter wait for ▶ Next — so the audience looks at exactly
    // what the narration describes for as long as the presenter wants.
    async beat(caption, action) {
      step += 1;
      const repaint = () => paintBar(pick(caption, lang));
      liveRepaint = repaint;
      await repaint().catch(() => {});
      if (action) await action();
      await repaint().catch(() => {});
      if (shotDir) {
        await page
          .screenshot({ path: `${shotDir}/beat-${String(step).padStart(2, "0")}.png` })
          .catch(() => {});
      }
      await waitForAdvance(repaint);
      await clearOverlay();
    },

    async title(title, subtitle) {
      const repaint = () => paintCard(pick(title, lang), pick(subtitle ?? "", lang));
      await repaint();
      await waitForAdvance(repaint);
      await clearOverlay();
    },

    async beatRetrying(message) {
      const repaint = () => paintFailBar(message, true);
      liveRepaint = repaint;
      await repaint().catch(() => {});
    },

    async beatFailed(message) {
      const repaint = () => paintFailBar(message);
      liveRepaint = repaint;
      clearFileSignals();
      await repaint().catch(() => {});
      for (;;) {
        if (consumeFileSignal("retry")) return "retry";
        if (consumeFileSignal("skip")) return "skip";
        if (!(await overlayPresent())) await repaint().catch(() => {});
        const choice = await page
          .evaluate(() => {
            const w = window as unknown as Record<string, unknown>;
            const out = w.__pRetry ? "retry" : w.__pSkip ? "skip" : null;
            w.__pRetry = false;
            w.__pSkip = false;
            return out;
          })
          .catch(() => null);
        if (choice === "retry" || choice === "skip") return choice;
        await page.waitForTimeout(POLL_MS);
      }
    },

    async stop() {
      liveRepaint = null;
      await clearOverlay();
    },
  };
}
