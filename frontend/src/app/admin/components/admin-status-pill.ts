import { SignalWatcher } from "@lit-labs/signals";
import { css, html, LitElement } from "lit";
import { property } from "lit/decorators.js";
type Tone = "free" | "busy" | "idle" | "bad";
const TONES: Record<string, Tone> = {
  ready: "free",
  active: "free",
  leased: "busy",
  starting: "busy",
  stopping: "busy",
  suspended: "idle",
  stopped: "idle",
  failed: "bad",
};
export class AdminStatusPill extends SignalWatcher(LitElement) {
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
        display: inline-flex;
      }
      span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        height: 20px;
        padding: 0 9px 0 7px;
        color: var(--admin-text-soft);
        font-family: var(--font-mono);
        font-size: 0.61rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        white-space: nowrap;
        background: var(--admin-raised);
        border: 1px solid var(--admin-line-strong);
        border-radius: 999px;
      }
      i {
        width: 5px;
        height: 5px;
        background: currentcolor;
        border-radius: 50%;
      }
      span[data-tone="free"] {
        color: var(--admin-free);
        background: rgb(88 168 110 / 10%);
        border-color: rgb(88 168 110 / 26%);
      }
      span[data-tone="busy"] {
        color: var(--admin-busy);
        background: rgb(198 154 75 / 10%);
        border-color: rgb(198 154 75 / 26%);
      }
      span[data-tone="bad"] {
        color: var(--admin-bad);
        background: rgb(203 105 98 / 10%);
        border-color: rgb(203 105 98 / 28%);
      }
    `,
  ];
  @property({ attribute: false })
  status!: string;
  protected get tone(): Tone {
    return TONES[this.status] ?? "idle";
  }
  protected render() {
    return html`
      <span data-tone=${this.tone}>
        <i aria-hidden="true"></i>
        ${this.status}
      </span>
    `;
  }
}
customElements.define("app-admin-status-pill", AdminStatusPill);
