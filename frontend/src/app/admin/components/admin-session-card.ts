import type { SessionResponse } from "@browsertunnel/backend-client";
import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { property } from "lit/decorators.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
import { relativeTime, shortId } from "../services/format";
import { adminActionStyles } from "./admin-action";
import "./admin-card";
import type { AdminFact } from "./admin-card";
export class AdminSessionCard extends SignalWatcher(LitElement) {
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
    `,
    adminActionStyles,
  ];
  @property({ attribute: false })
  session!: SessionResponse;
  private readonly consoleConsumer = new ContextConsumer(this, {
    context: adminConsoleContext,
    subscribe: true,
  });
  protected get console(): AdminConsole {
    const value = this.consoleConsumer.value;
    if (!value) throw new Error("Missing AdminConsole provider");
    return value;
  }
  protected get label() {
    return shortId(this.session.id);
  }
  protected get busy() {
    return this.console.isBusy(this.session.id);
  }
  protected get facts(): readonly AdminFact[] {
    const session = this.session;
    return [
      { label: "Owner", value: shortId(session.owner_id), full: session.owner_id, id: true },
      {
        label: "Browser",
        value: session.browser_id ? shortId(session.browser_id) : "—",
        full: session.browser_id ?? undefined,
        id: true,
      },
      { label: "Opened", value: relativeTime(session.created_at) },
      { label: "Expires", value: session.expires_at ? relativeTime(session.expires_at) : "—" },
    ];
  }
  protected render() {
    return html`
      <app-admin-card
        .heading=${this.label}
        .full=${this.session.id}
        .status=${this.session.status}
        .facts=${this.facts}
        .busy=${this.busy}
      >
        ${
          this.session.status === "active"
            ? html`
                <button
                  appAdminAction=""
                  ?disabled=${this.busy}
                  @click=${(event: MouseEvent) => {
                    this.console.suspendSession(this.session.id);
                  }}
                >
                  Suspend
                </button>
              `
            : html`
                <button
                  appAdminAction=""
                  ?disabled=${this.busy}
                  @click=${(event: MouseEvent) => {
                    this.console.resumeSession(this.session.id);
                  }}
                >
                  Resume
                </button>
              `
        }<button
          appAdminAction=""
          ?disabled=${this.busy}
          @click=${(event: MouseEvent) => {
            this.console.closeSession(this.session.id);
          }}
        >
          Close
        </button>
      </app-admin-card>
    `;
  }
}
customElements.define("app-admin-session-card", AdminSessionCard);
