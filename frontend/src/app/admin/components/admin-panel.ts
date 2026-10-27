import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement, nothing } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
import { clockTime } from "../services/format";
import { adminActionStyles } from "./admin-action";
import "./admin-browser-grid";
import "./admin-checkpoint-list";
import "./admin-notice";
import "./admin-session-grid";
import "./admin-stat-strip";
const POLL_INTERVAL_MS = 5000;
export class AdminPanel extends SignalWatcher(LitElement) {
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
        --admin-surface: #0e1117;
        --admin-raised: #171b22;
        --admin-hover: #1f242c;
        --admin-line: #1e242d;
        --admin-line-strong: #2b323c;
        --admin-line-bright: #3c434f;
        --admin-text: #e6eaf1;
        --admin-text-soft: #b3bac5;
        --admin-text-dim: #6e757f;
        --admin-text-faint: #565c65;
        --admin-free: #77bb8a;
        --admin-busy: #d3a95f;
        --admin-bad: #d5837a;
        --admin-focus: #79a4ff;
        --admin-radius: 12px;

        display: block;
      }
      .admin {
        display: grid;
        gap: clamp(16px, 1.8vw, 24px);
        width: min(100%, 1180px);
        margin-inline: auto;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
      }
      hgroup {
        display: grid;
        gap: 4px;
        min-width: 0;
        margin: 0;
      }
      h1 {
        margin: 0;
        color: var(--admin-text);
        font-size: 1rem;
        font-weight: 650;
        letter-spacing: -0.02em;
      }
      hgroup p {
        margin: 0;
        color: var(--admin-text-dim);
        font-size: 0.73rem;
        line-height: 1.5;
      }
      .controls {
        display: inline-flex;
        align-items: center;
        gap: 10px;
      }
      .controls small {
        color: var(--admin-text-faint);
        font-family: var(--font-mono);
        font-size: 0.65rem;
        white-space: nowrap;
      }
      .spinner {
        width: 10px;
        height: 10px;
        border: 1.5px solid currentcolor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spin 650ms linear infinite;
      }
      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .spinner {
          animation-duration: 1.6s;
        }
      }
    `,
    adminActionStyles,
  ];
  @property({ attribute: false })
  active: boolean = false;
  private readonly consoleConsumer = new ContextConsumer(this, {
    context: adminConsoleContext,
    subscribe: true,
  });
  protected get console(): AdminConsole {
    const value = this.consoleConsumer.value;
    if (!value) throw new Error("Missing AdminConsole provider");
    return value;
  }
  protected get updatedAt() {
    const refreshed = this.console.refreshedAt.get();
    return refreshed && clockTime(refreshed);
  }
  private refreshTimer?: ReturnType<typeof setInterval>;
  protected updated(): void {
    if (this.active && !this.refreshTimer) {
      queueMicrotask(() => {
        if (this.isConnected && this.active) void this.console.refresh();
      });
      this.refreshTimer = setInterval(() => void this.console.refresh(), POLL_INTERVAL_MS);
    } else if (!this.active && this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = undefined;
    }
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    clearInterval(this.refreshTimer);
    this.refreshTimer = undefined;
  }
  protected render() {
    return html`
      <div class=${classMap({ admin: true })}>
        <header>
          <hgroup>
            <h1>Browser infrastructure</h1>
            <p>Every provisioned browser and the sessions on it — the state, not a live picture.</p>
          </hgroup>

          <div class=${classMap({ controls: true })}>
            ${((stamp) => (stamp ? html` <small>Updated ${stamp}</small> ` : nothing))(
              this.updatedAt,
            )}<button
              appAdminAction=""
              ?disabled=${this.console.loading.get()}
              @click=${(event: MouseEvent) => {
                this.console.refresh();
              }}
            >
              ${
                this.console.loading.get()
                  ? html` <i aria-hidden="true" class=${classMap({ spinner: true })}></i> `
                  : nothing
              }
              Refresh
            </button>
          </div>
        </header>

        <app-admin-notice></app-admin-notice>
        <app-admin-stat-strip></app-admin-stat-strip>
        <app-admin-browser-grid></app-admin-browser-grid>
        <app-admin-session-grid></app-admin-session-grid>
        <app-admin-checkpoint-list></app-admin-checkpoint-list>
      </div>
    `;
  }
}
customElements.define("app-admin-panel", AdminPanel);
