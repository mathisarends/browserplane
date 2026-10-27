import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
import "./admin-browser-card";
import "./admin-section";
export class AdminBrowserGrid extends SignalWatcher(LitElement) {
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
    const total = this.console.browsers.get().length;
    return `${this.console.availableBrowsers.get().length} of ${total} available`;
  }
  protected render() {
    return html`
      <app-admin-section heading="Browser pool" .meta=${this.meta}>
        <div class=${classMap({ cards: true })}>
          ${
            this.console.browsers.get().length
              ? repeat(
                  this.console.browsers.get(),
                  (browser, index) => browser.id,
                  (browser, index) => html`
                    <app-admin-browser-card .browser=${browser}></app-admin-browser-card>
                  `,
                )
              : html`
                  <p class=${classMap({ empty: true })}>
                    ${this.console.loaded.get() ? "No browsers are provisioned." : "Loading the pool…"}
                  </p>
                `
          }
        </div>
      </app-admin-section>
    `;
  }
}
customElements.define("app-admin-browser-grid", AdminBrowserGrid);
