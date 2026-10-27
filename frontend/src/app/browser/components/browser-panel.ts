import { signal, SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer, ContextProvider } from "@lit/context";
import { queryClientContext } from "@tanstack/lit-query";
import { css, html, LitElement, nothing } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import {
  browserSessionContext,
  clientIdentityContext,
  screencastModeContext,
} from "../../shared/contexts";
import { BrowserSession } from "../services/browser-session";
import "./browser-canvas";
import "./browser-navigation-bar";
import type { BrowserNavigationBar } from "./browser-navigation-bar";
import "./browser-state-toolbar";
import "./browser-stream-badge";
import "./browser-tab-strip";
import "./browser-transfer-toolbar";
export class BrowserPanel extends SignalWatcher(LitElement) {
  private readonly identityConsumer = new ContextConsumer(this, {
    context: clientIdentityContext,
    subscribe: true,
  });
  private readonly modeConsumer = new ContextConsumer(this, {
    context: screencastModeContext,
    subscribe: true,
  });
  private readonly sessionProvider = new ContextProvider(this, { context: browserSessionContext });
  private readonly queryClientConsumer = new ContextConsumer(this, {
    context: queryClientContext,
    subscribe: true,
  });
  private ownedSession?: BrowserSession;
  protected get session(): BrowserSession {
    if (!this.ownedSession) {
      this.ownedSession = new BrowserSession(
        this.identityConsumer.value!,
        this.modeConsumer.value!,
        this.queryClientConsumer.value!,
      );
      this.sessionProvider.setValue(this.ownedSession);
    }
    return this.ownedSession;
  }
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
      .browser-panel {
        overflow: hidden;
        background: #11151c;
        border: 1px solid #252d3a;
        border-radius: 14px;
        box-shadow: 0 28px 80px rgb(0 0 0 / 34%);
      }
      .browser-chrome {
        background: linear-gradient(180deg, #1a202a, #171c24);
      }
      .session-error {
        margin: 0;
        padding: 7px 12px;
        color: #f0c9c9;
        font-size: 0.74rem;
        background: rgb(58 26 26 / 62%);
        border-top: 1px solid #6b3232;
      }
      .request-state {
        display: flex;
        aspect-ratio: 16 / 9;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        gap: 10px;
        padding: 28px;
        color: #929fb2;
        text-align: center;
        background:
          radial-gradient(circle at 50% 42%, rgb(52 73 108 / 24%), transparent 34%), #080b10;
      }
      .request-state strong {
        color: #e7edf7;
        font-size: 1rem;
        font-weight: 600;
      }
      .request-state span:last-child {
        max-width: 34ch;
        font-size: 0.82rem;
        line-height: 1.5;
      }
      .request-spinner {
        width: 28px;
        height: 28px;
        margin-bottom: 4px;
        border: 2px solid #283143;
        border-top-color: #6797ff;
        border-radius: 50%;
        animation: request-spin 900ms linear infinite;
      }
      @keyframes request-spin {
        to {
          transform: rotate(360deg);
        }
      }
      @media (max-width: 580px) {
        .browser-panel {
          border-radius: 10px;
        }
      }
      @media (prefers-reduced-motion: no-preference) {
        .browser-panel {
          animation: panel-enter 420ms both;
        }
        @keyframes panel-enter {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .request-spinner {
          animation: none;
          border-color: #6797ff;
        }
      }
    `,
  ];
  @property({ attribute: false })
  panelId!: string;
  @property({ attribute: false })
  sessionId: string | undefined = undefined;
  protected readonly address = signal("");
  protected get label() {
    return this.session.browserId.get() ?? "No session";
  }
  protected get waiting() {
    const status = this.session.requestStatus.get();
    return status === "QUEUED" || status === "PROVISIONING";
  }
  private get navigationBar(): BrowserNavigationBar | undefined {
    return (
      this.renderRoot.querySelector<BrowserNavigationBar>('[data-ref="navigationBar"]') ?? undefined
    );
  }
  firstUpdated(): void {
    void this.connect();
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    void this.session.disconnect();
  }
  protected navigate(): void {
    const value = this.address.get().trim();
    if (value) void this.session.navigate(value);
  }
  protected async createTab(): Promise<void> {
    await this.session.createTab();
    this.navigationBar?.focusAddress();
  }
  private async connect(): Promise<void> {
    const sessionId = this.sessionId;
    if (sessionId) {
      if (!(await this.session.attach(sessionId)))
        this.dispatchEvent(
          new CustomEvent("session-lost", { detail: this.panelId, bubbles: true, composed: true }),
        );
      return;
    }
    const remainingCapacity = await this.session.open();
    if (remainingCapacity === undefined) {
      this.dispatchEvent(
        new CustomEvent("session-lost", { detail: this.panelId, bubbles: true, composed: true }),
      );
      return;
    }
    this.dispatchEvent(
      new CustomEvent("capacity-change", {
        detail: remainingCapacity,
        bubbles: true,
        composed: true,
      }),
    );
  }
  private previousUrl?: string;
  protected willUpdate(): void {
    const url = this.session.page.activeUrl.get();
    if (url !== this.previousUrl) {
      this.previousUrl = url;
      queueMicrotask(() => this.address.set(url));
    }
  }
  protected render() {
    return html`
      <section aria-label=${this.label + " preview"} class=${classMap({ "browser-panel": true })}>
        <header class=${classMap({ "browser-chrome": true })}>
          <app-browser-tab-strip
            .tabs=${this.session.page.tabs.get()}
            @activate=${(event: CustomEvent) => {
              this.session.activateTab(event.detail);
            }}
            @close=${(event: CustomEvent) => {
              this.session.closeTab(event.detail);
            }}
            @create=${(event: CustomEvent) => {
              this.createTab();
            }}
          ></app-browser-tab-strip>
          <app-browser-navigation-bar
            data-ref="navigationBar"
            .panelId=${this.panelId}
            .address=${this.address.get()}
            .navigation=${this.session.page.navigation.get()}
            .hasActiveTab=${!!this.session.page.activeTab.get()}
            @address-change=${(event: CustomEvent) => {
              this.address.set(event.detail);
            }}
            @navigate=${(event: CustomEvent) => {
              this.navigate();
            }}
            @back=${(event: CustomEvent) => {
              this.session.back();
            }}
            @forward=${(event: CustomEvent) => {
              this.session.forward();
            }}
            @reload-or-stop=${(event: CustomEvent) => {
              this.session.reloadOrStop();
            }}
          ></app-browser-navigation-bar>
        </header>

        ${
          this.waiting
            ? html`
                <div role="status" aria-live="polite" class=${classMap({ "request-state": true })}>
                  <span aria-hidden="true" class=${classMap({ "request-spinner": true })}></span>
                  ${
                    this.session.requestStatus.get() === "QUEUED"
                      ? html`
                          <strong>Waiting for capacity</strong>
                          <span
                            >All browser slots are busy. This browser will start
                            automatically.</span
                          >
                        `
                      : html`
                          <strong>Starting browser</strong>
                          <span>Capacity is reserved and the browser is being prepared.</span>
                        `
                  }
                </div>
              `
            : html`
                <app-browser-canvas></app-browser-canvas>
                ${((message) =>
                  message
                    ? html`
                        <p role="status" class=${classMap({ "session-error": true })}>${message}</p>
                      `
                    : nothing)(this.session.error.get())}<app-browser-stream-badge
                ></app-browser-stream-badge>
                <app-browser-transfer-toolbar></app-browser-transfer-toolbar>
                <app-browser-state-toolbar></app-browser-state-toolbar>
              `
        }
      </section>
    `;
  }
}
customElements.define("app-browser-panel", BrowserPanel);
