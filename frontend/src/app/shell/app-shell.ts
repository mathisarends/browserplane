import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { classMap } from "lit/directives/class-map.js";
import "../admin/components/admin-panel";
import "../browser/layouts/browser-layout";
import { appViewContext } from "../shared/contexts";
import "./shell-view-switcher";
import { AppViewState } from "./view-mode";
export class AppShell extends SignalWatcher(LitElement) {
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
      .shell {
        width: 100%;
        padding: 6px clamp(10px, 1.4vw, 26px) clamp(16px, 2vw, 32px);
      }
      .pane.is-hidden {
        display: none;
      }
      @media (max-width: 580px) {
        .shell {
          padding: 4px 8px 14px;
        }
      }
    `,
  ];
  private readonly viewsConsumer = new ContextConsumer(this, {
    context: appViewContext,
    subscribe: true,
  });
  protected get views(): AppViewState {
    const value = this.viewsConsumer.value;
    if (!value) throw new Error("Missing AppViewState provider");
    return value;
  }
  protected render() {
    return html`
      <div class=${classMap({ shell: true })}>
        <app-shell-view-switcher
          .view=${this.views.view.get()}
          @view-change=${(event: CustomEvent) => {
            this.views.select(event.detail);
          }}
        ></app-shell-view-switcher>

        <div
          class=${classMap({ pane: true, "is-hidden": Boolean(this.views.view.get() === "admin") })}
        >
          <app-browser-layout .focused=${this.views.view.get() === "focus"}></app-browser-layout>
        </div>
        <div
          class=${classMap({ pane: true, "is-hidden": Boolean(this.views.view.get() !== "admin") })}
        >
          <app-admin-panel .active=${this.views.view.get() === "admin"}></app-admin-panel>
        </div>
      </div>
    `;
  }
}
customElements.define("app-shell", AppShell);
