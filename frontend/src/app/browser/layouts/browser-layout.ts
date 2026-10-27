import { type SessionResponse } from "@browsertunnel/backend-client";
import { signal, SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { createQueryController } from "@tanstack/lit-query";
import { css, html, LitElement, nothing } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import { clientIdentityContext } from "../../shared/contexts";
import "../components/browser-create-tile";
import "../components/browser-panel";
import { ownerSessionsQuery } from "../queries/owner-sessions";
import { ClientIdentity } from "../services/client-identity";
interface GalleryPanel {
  readonly key: string;
  readonly sessionId?: string;
}
export class BrowserLayout extends SignalWatcher(LitElement) {
  static styles = [
    css`
      :host,
      * {
        box-sizing: border-box;
      }
      button,
      input,
      select {
        font: inherit;
      }
    `,
    css`
      :host {
        display: block;
      }
      .browser-stage {
        width: min(100%, 2560px);
        min-width: 0;
        margin-inline: auto;
      }
      .carousel {
        display: block;
        min-width: 0;
      }
      .carousel.is-focused {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: clamp(8px, 1.2vw, 20px);
      }
      .browser-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: clamp(14px, 1.5vw, 22px);
        min-width: 0;
        animation: grid-enter 380ms cubic-bezier(0.22, 1, 0.36, 1) both;
      }
      .browser-grid.is-focused {
        grid-template-columns: minmax(0, 1fr);
        width: min(100%, 1680px);
      }
      .browser-grid.is-focused > .is-offstage {
        display: none;
      }
      .chevron {
        display: grid;
        place-items: center;
        flex: none;
        width: clamp(38px, 3.2vw, 52px);
        height: clamp(38px, 3.2vw, 52px);
        color: #c5c8cf;
        background: #16181d;
        border: 1px solid #2b2d31;
        border-radius: 999px;
        cursor: pointer;
        transition:
          color 180ms ease,
          background 180ms ease,
          opacity 180ms ease;
      }
      .chevron svg {
        width: 22px;
        height: 22px;
        fill: none;
        stroke: currentcolor;
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      .chevron:hover:not(:disabled) {
        color: #f4f5f7;
        background: #22252a;
      }
      .chevron:disabled {
        opacity: 35%;
        cursor: default;
      }
      .chevron:focus-visible {
        outline: 2px solid #79a4ff;
        outline-offset: 2px;
      }
      .focus-counter {
        margin: clamp(10px, 1.2vw, 18px) 0 0;
        color: #686e79;
        font-size: 0.72rem;
        font-variant-numeric: tabular-nums;
        text-align: center;
      }
      .restore-notice {
        margin: 0 0 12px;
        padding: 9px 14px;
        color: #f0c9c9;
        font-size: 0.82rem;
        background: rgb(58 26 26 / 62%);
        border: 1px solid #6b3232;
        border-radius: 10px;
      }
      .browser-grid app-browser-panel,
      .browser-grid app-browser-create-tile {
        min-width: 0;
      }
      @keyframes grid-enter {
        from {
          opacity: 0;
          transform: scale(0.985);
        }
        to {
          opacity: 1;
          transform: scale(1);
        }
      }
      @media (max-width: 580px) {
        .browser-grid {
          grid-template-columns: minmax(0, 1fr);
          gap: 14px;
        }
        .carousel.is-focused {
          gap: 6px;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .browser-grid {
          animation: none;
        }
        .chevron {
          transition: none;
        }
      }
    `,
  ];
  @property({ attribute: false })
  focused: boolean = false;
  private readonly identityConsumer = new ContextConsumer(this, {
    context: clientIdentityContext,
    subscribe: true,
  });
  protected get identity(): ClientIdentity {
    const value = this.identityConsumer.value;
    if (!value) throw new Error("Missing ClientIdentity provider");
    return value;
  }
  protected readonly panels = signal<readonly GalleryPanel[]>([]);
  protected readonly restoreFailed = signal(false);
  private readonly restoring = signal(true);
  private readonly creating = signal(false);
  protected get canCreate() {
    return !this.restoring.get() && !this.creating.get();
  }
  protected get slideCount() {
    return this.panels.get().length + (this.canCreate ? 1 : 0);
  }
  private readonly requestedIndex = signal(0);
  protected get focusIndex() {
    return Math.min(this.requestedIndex.get(), Math.max(0, this.slideCount - 1));
  }
  private readonly ownedSessions = createQueryController(this, () => ({
    ...ownerSessionsQuery(this.identity.ownerId),
    enabled: this.restoring.get(),
  }));

  protected updated(): void {
    const result = this.ownedSessions();
    if (!this.restoring.get() || result.isPending) return;
    const data = result.data;
    queueMicrotask(() => {
      if (!this.isConnected || !this.restoring.get()) return;
      if (data)
        this.panels.set(
          [...data.sessions]
            .sort(byAge)
            .map((session) => ({ key: session.id, sessionId: session.id })),
        );
      else this.restoreFailed.set(true);
      this.restoring.set(false);
    });
  }
  protected step(direction: 1 | -1): void {
    const count = this.slideCount;
    if (count < 2) return;
    this.requestedIndex.set((this.focusIndex + direction + count) % count);
  }
  protected createBrowser(): void {
    if (!this.canCreate) return;
    this.creating.set(true);
    this.panels.set(((panels) => [...panels, { key: crypto.randomUUID() }])(this.panels.get()));
    if (this.focused) this.requestedIndex.set(this.panels.get().length - 1);
  }
  protected handleCapacityChange(_remainingCapacity: number): void {
    this.creating.set(false);
  }
  protected handleSessionLost(key: string): void {
    this.panels.set(((panels) => panels.filter((panel) => panel.key !== key))(this.panels.get()));
    this.creating.set(false);
  }

  protected render() {
    return html`
      <main aria-label="Remote Browser Sessions" class=${classMap({ "browser-stage": true })}>
        ${
          this.restoreFailed.get()
            ? html`
                <p role="status" class=${classMap({ "restore-notice": true })}>
                  Sessions already running could not be loaded. Reload the page to try again.
                </p>
              `
            : nothing
        }
        <div class=${classMap({ carousel: true, "is-focused": Boolean(this.focused) })}>
          ${
            this.focused
              ? html`
                  <button
                    type="button"
                    aria-label="Previous browser"
                    ?disabled=${this.slideCount < 2}
                    class=${classMap({ chevron: true })}
                    @click=${(event: MouseEvent) => {
                      this.step(-1);
                    }}
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M15 5l-7 7 7 7"></path>
                    </svg>
                  </button>
                `
              : nothing
          }
          <div class=${classMap({ "browser-grid": true, "is-focused": Boolean(this.focused) })}>
            ${repeat(
              this.panels.get(),
              (panel, index) => panel.key,
              (panel, index) => html`
                <app-browser-panel
                  .panelId=${panel.key}
                  .sessionId=${panel.sessionId}
                  class=${classMap({ "is-offstage": Boolean(this.focused && this.focusIndex !== index) })}
                  @capacity-change=${(event: CustomEvent) => {
                    this.handleCapacityChange(event.detail);
                  }}
                  @session-lost=${(event: CustomEvent) => {
                    this.handleSessionLost(event.detail);
                  }}
                ></app-browser-panel>
              `,
            )}${
              this.canCreate
                ? html`
                    <app-browser-create-tile
                      class=${classMap({ "is-offstage": Boolean(this.focused && this.focusIndex !== this.panels.get().length) })}
                      @create=${(event: CustomEvent) => {
                        this.createBrowser();
                      }}
                    ></app-browser-create-tile>
                  `
                : nothing
            }
          </div>
          ${
            this.focused
              ? html`
                  <button
                    type="button"
                    aria-label="Next browser"
                    ?disabled=${this.slideCount < 2}
                    class=${classMap({ chevron: true })}
                    @click=${(event: MouseEvent) => {
                      this.step(1);
                    }}
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"></path></svg>
                  </button>
                `
              : nothing
          }
        </div>
        ${
          this.focused && this.slideCount > 0
            ? html`
                <p role="status" aria-live="polite" class=${classMap({ "focus-counter": true })}>
                  ${this.focusIndex + 1} / ${this.slideCount}
                </p>
              `
            : nothing
        }
      </main>
    `;
  }
}
function byAge(left: SessionResponse, right: SessionResponse): number {
  return left.created_at.localeCompare(right.created_at);
}
customElements.define("app-browser-layout", BrowserLayout);
