import { SignalWatcher } from "@lit-labs/signals";
import { css, html, LitElement, nothing } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import type { BrowserTabState } from "../services/browser-page-state";
export class BrowserTabStrip extends SignalWatcher(LitElement) {
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
        display: flex;
        align-items: flex-end;
        gap: 10px;
        height: 38px;
        padding: 4px 12px 0 14px;
        background: #17191e;
      }
      .window-controls {
        display: flex;
        flex: 0 0 58px;
        align-self: center;
        gap: 7px;
      }
      .window-controls span {
        width: 10px;
        height: 10px;
        background: #454b57;
        border-radius: 50%;
        box-shadow: inset 0 0 0 0.5px rgb(0 0 0 / 28%);
      }
      .window-controls span:first-child {
        background: #ff5f57;
      }
      .window-controls span:nth-child(2) {
        background: #febc2e;
      }
      .window-controls span:last-child {
        background: #28c840;
      }
      .tabs {
        display: flex;
        overflow: hidden;
        align-items: center;
        flex: 1;
        min-width: 0;
        height: 34px;
      }
      .tab-list {
        display: flex;
        overflow-x: auto;
        flex: 0 1 auto;
        min-width: 0;
        gap: 3px;
        scrollbar-width: none;
      }
      .browser-tab {
        display: grid;
        grid-template-columns: 14px minmax(0, 1fr) 22px;
        align-items: center;
        gap: 7px;
        flex: 0 1 230px;
        width: 230px;
        min-width: 120px;
        max-width: 250px;
        height: 34px;
        padding: 0 5px 0 11px;
        color: #8f949d;
        background: transparent;
        border: 1px solid transparent;
        border-bottom: 0;
        border-radius: 9px 9px 0 0;
        cursor: default;
        outline: none;
      }
      .browser-tab[aria-selected="true"] {
        color: #f0f1f3;
        background: #26282d;
        border-color: #30333a;
        box-shadow: inset 0 1px 0 rgb(255 255 255 / 3%);
      }
      .browser-tab:focus-visible {
        box-shadow: inset 0 0 0 1px #79a4ff;
      }
      .tab-icon {
        position: relative;
        width: 14px;
        height: 14px;
      }
      .tab-icon i {
        position: absolute;
        inset: 3.5px;
        width: 7px;
        height: 7px;
        background: #666c76;
        border-radius: 50%;
      }
      .browser-tab[aria-selected="true"] .tab-icon i {
        background: #b8bdc6;
      }
      .tab-icon img {
        position: absolute;
        inset: 0;
        width: 14px;
        height: 14px;
        object-fit: contain;
      }
      .browser-tab > span {
        overflow: hidden;
        font-size: 0.75rem;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .close-tab,
      .new-tab {
        display: grid;
        place-items: center;
        color: #81868f;
        background: transparent;
        border: 0;
        border-radius: 999px;
        cursor: pointer;
      }
      .close-tab:hover,
      .new-tab:hover {
        color: #f0f1f3;
        background: #303238;
      }
      .close-tab:focus-visible,
      .new-tab:focus-visible {
        outline: 2px solid #79a4ff;
        outline-offset: 1px;
      }
      .close-tab {
        width: 22px;
        height: 22px;
        padding: 0 0 2px;
        font-size: 1.06rem;
      }
      .new-tab {
        flex: 0 0 28px;
        width: 28px;
        height: 28px;
        margin: 0 0 2px 5px;
        font-size: 1.12rem;
      }
      @media (max-width: 580px) {
        :host {
          gap: 6px;
          height: 36px;
          padding: 4px 8px 0 10px;
        }
        .window-controls {
          flex-basis: 43px;
          gap: 5px;
        }
        .window-controls span {
          width: 8px;
          height: 8px;
        }
        .browser-tab {
          min-width: 105px;
          height: 32px;
        }
      }
    `,
  ];
  @property({ attribute: false })
  tabs!: readonly BrowserTabState[];
  protected render() {
    return html`
      <div aria-hidden="true" class=${classMap({ "window-controls": true })}>
        <span></span><span></span><span></span>
      </div>
      <div class=${classMap({ tabs: true })}>
        <div role="tablist" aria-label="Browser tabs" class=${classMap({ "tab-list": true })}>
          ${repeat(
            this.tabs,
            (tab, index) => tab.id,
            (tab, index) => html`
              <div
                role="tab"
                .tabIndex=${tab.active ? 0 : -1}
                aria-selected=${tab.active}
                class=${classMap({ "browser-tab": true })}
                @click=${(event: MouseEvent) => {
                  this.dispatchEvent(
                    new CustomEvent("activate", { detail: tab.id, bubbles: true, composed: true }),
                  );
                }}
              >
                <span aria-hidden="true" class=${classMap({ "tab-icon": true })}>
                  <i></i>
                  ${
                    tab.faviconUrl
                      ? html`
                          <img
                            alt=""
                            referrerpolicy="no-referrer"
                            .src=${tab.faviconUrl}
                            @load=${(event: Event) => {
                              (event.target as any).hidden = false;
                            }}
                            @error=${(event: Event) => {
                              (event.target as any).hidden = true;
                            }}
                          />
                        `
                      : nothing
                  }</span
                >
                <span>${tab.title || "New tab"}</span>
                <button
                  type="button"
                  aria-label=${"Close " + (tab.title || "new tab")}
                  class=${classMap({ "close-tab": true })}
                  @click=${(event: MouseEvent) => {
                    event.stopPropagation();
                    this.dispatchEvent(
                      new CustomEvent("close", { detail: tab.id, bubbles: true, composed: true }),
                    );
                  }}
                >
                  ×
                </button>
              </div>
            `,
          )}
        </div>
        <button
          type="button"
          aria-label="Open new tab"
          class=${classMap({ "new-tab": true })}
          @click=${(event: MouseEvent) => {
            this.dispatchEvent(
              new CustomEvent("create", { detail: undefined, bubbles: true, composed: true }),
            );
          }}
        >
          +
        </button>
      </div>
    `;
  }
}
customElements.define("app-browser-tab-strip", BrowserTabStrip);
