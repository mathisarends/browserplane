import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { repeat } from "lit/directives/repeat.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
type Tone = "plain" | "free" | "busy" | "bad";
type Stat = {
  readonly label: string;
  readonly value: number;
  readonly tone: Tone;
};
export class AdminStatStrip extends SignalWatcher(LitElement) {
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
      dl {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
        gap: 1px;
        margin: 0;
        overflow: hidden;
        background: var(--admin-line);
        border: 1px solid var(--admin-line);
        border-radius: var(--admin-radius);
      }
      div {
        display: flex;
        align-items: baseline;
        gap: 8px;
        padding: 11px 14px;
        background: var(--admin-surface);
      }
      dd {
        order: -1;
        margin: 0;
        color: var(--admin-text);
        font-size: 1rem;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.02em;
        line-height: 1;
      }
      dt {
        color: var(--admin-text-dim);
        font-size: 0.68rem;
        white-space: nowrap;
      }
      div[data-tone="free"] dd {
        color: var(--admin-free);
      }
      div[data-tone="busy"] dd {
        color: var(--admin-busy);
      }
      div[data-tone="bad"] dd {
        color: var(--admin-bad);
      }
    `,
  ];
  private readonly consoleConsumer = new ContextConsumer(this, {
    context: adminConsoleContext,
    subscribe: true,
  });
  protected get console(): AdminConsole {
    const value = this.consoleConsumer.value;
    if (!value) throw new Error("Missing AdminConsole provider");
    return value;
  }
  protected get stats(): readonly Stat[] {
    return [
      { label: "Browsers", value: this.console.browsers.get().length, tone: "plain" },
      { label: "Available", value: this.console.availableBrowsers.get().length, tone: "free" },
      { label: "Active", value: this.console.activeSessions.get().length, tone: "busy" },
      { label: "Suspended", value: this.console.suspendedSessions.get().length, tone: "plain" },
      { label: "Offline", value: this.console.offlineBrowsers.get().length, tone: "bad" },
      { label: "Checkpoints", value: this.console.checkpoints.get().length, tone: "plain" },
    ];
  }
  protected render() {
    return html`
      <dl aria-label="Pool summary">
        ${repeat(
          this.stats,
          (stat, index) => stat.label,
          (stat, index) => html`
            <div data-tone=${stat.tone}>
              <dt>${stat.label}</dt>
              <dd>${stat.value}</dd>
            </div>
          `,
        )}
      </dl>
    `;
  }
}
customElements.define("app-admin-stat-strip", AdminStatStrip);
