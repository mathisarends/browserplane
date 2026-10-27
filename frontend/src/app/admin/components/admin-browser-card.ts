import type { PooledBrowserResponse } from "@browsertunnel/backend-client";
import { signal, SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
import { relativeTime, shortId } from "../services/format";
import { adminActionStyles } from "./admin-action";
import "./admin-card";
import type { AdminFact } from "./admin-card";
export class AdminBrowserCard extends SignalWatcher(LitElement) {
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
      .prompt {
        margin-right: auto;
        color: var(--admin-text-dim);
        font-size: 0.68rem;
      }
    `,
    adminActionStyles,
  ];
  @property({ attribute: false })
  browser!: PooledBrowserResponse;
  private readonly consoleConsumer = new ContextConsumer(this, {
    context: adminConsoleContext,
    subscribe: true,
  });
  protected get console(): AdminConsole {
    const value = this.consoleConsumer.value;
    if (!value) throw new Error("Missing AdminConsole provider");
    return value;
  }
  protected readonly confirming = signal(false);
  protected get label() {
    return shortId(this.browser.id);
  }
  protected get busy() {
    return this.console.isBusy(this.browser.id);
  }
  protected get facts(): readonly AdminFact[] {
    const lease = this.browser.lease;
    return [
      { label: "Provisioned", value: relativeTime(this.browser.created_at) },
      {
        label: "Held by",
        value: lease ? shortId(lease.session_id) : "—",
        full: lease?.session_id,
        id: true,
      },
      {
        label: "Owner",
        value: lease ? shortId(lease.owner_id) : "—",
        full: lease?.owner_id,
        id: true,
      },
      { label: "Lease ends", value: lease ? relativeTime(lease.expires_at) : "—" },
    ];
  }
  protected async release(): Promise<void> {
    this.confirming.set(false);
    await this.console.releaseBrowser(this.browser.id);
  }
  protected render() {
    return html`
      <app-admin-card
        .heading=${this.label}
        .full=${this.browser.id}
        .status=${this.browser.state}
        .facts=${this.facts}
        .busy=${this.busy}
      >
        ${
          this.confirming.get()
            ? html`
                <span class=${classMap({ prompt: true })}>Release this browser?</span>
                <button
                  appAdminAction=""
                  @click=${(event: MouseEvent) => {
                    this.confirming.set(false);
                  }}
                >
                  Cancel
                </button>
                <button
                  appAdminAction=""
                  data-tone="danger"
                  ?disabled=${this.busy}
                  @click=${(event: MouseEvent) => {
                    this.release();
                  }}
                >
                  Release
                </button>
              `
            : html`
                <button
                  appAdminAction=""
                  ?disabled=${this.busy}
                  @click=${(event: MouseEvent) => {
                    this.console.restartBrowser(this.browser.id);
                  }}
                >
                  Restart
                </button>
                <button
                  appAdminAction=""
                  ?disabled=${this.busy}
                  @click=${(event: MouseEvent) => {
                    this.confirming.set(true);
                  }}
                >
                  Release
                </button>
              `
        }</app-admin-card
      >
    `;
  }
}
customElements.define("app-admin-browser-card", AdminBrowserCard);
