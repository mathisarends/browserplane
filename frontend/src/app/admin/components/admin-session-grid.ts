import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
import "./admin-section";
import "./admin-session-card";
export class AdminSessionGrid extends SignalWatcher(LitElement) {
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
      .cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(258px, 1fr));
        gap: 10px;
      }
      .empty {
        grid-column: 1 / -1;
        padding: 26px 16px;
        margin: 0;
        color: var(--admin-text-dim);
        font-size: 0.72rem;
        text-align: center;
        border: 1px dashed var(--admin-line);
        border-radius: var(--admin-radius);
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
  protected get meta() {
    return (
      `${this.console.activeSessions.get().length} active · ` +
      `${this.console.suspendedSessions.get().length} suspended`
    );
  }
  protected render() {
    return html`
      <app-admin-section heading="Sessions" .meta=${this.meta}>
        <div class=${classMap({ cards: true })}>
          ${
            this.console.sessions.get().length
              ? repeat(
                  this.console.sessions.get(),
                  (session, index) => session.id,
                  (session, index) => html`
                    <app-admin-session-card .session=${session}></app-admin-session-card>
                  `,
                )
              : html`
                  <p class=${classMap({ empty: true })}>
                    ${this.console.loaded.get() ? "No session is open right now." : "Loading sessions…"}
                  </p>
                `
          }
        </div>
      </app-admin-section>
    `;
  }
}
customElements.define("app-admin-session-grid", AdminSessionGrid);
