import { SignalWatcher } from "@lit-labs/signals";
import { css, html, LitElement } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { live } from "lit/directives/live.js";
import type { NavigationState } from "../services/browser-page-state";
import { isAddress } from "../services/navigation-target";
export class BrowserNavigationBar extends SignalWatcher(LitElement) {
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
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        gap: 10px;
        min-height: 46px;
        padding: 7px 12px 8px;
        border-bottom: 1px solid #262c36;
        box-shadow: 0 1px 0 rgb(255 255 255 / 3%);
      }
      .navigation-controls {
        display: flex;
        align-items: center;
        gap: 2px;
      }
      button {
        display: grid;
        place-items: center;
        width: 30px;
        height: 30px;
        padding: 0;
        color: #aeb7c4;
        background: transparent;
        border: 0;
        border-radius: 50%;
        cursor: pointer;
        transition:
          color 140ms ease,
          background-color 140ms ease;
      }
      button:hover:not(:disabled) {
        color: #f0f3f7;
        background: #2c323d;
      }
      button:active:not(:disabled) {
        background: #353c48;
      }
      button:disabled {
        color: #4b525d;
        cursor: default;
      }
      button:focus-visible {
        outline: 2px solid #79a4ff;
        outline-offset: 1px;
      }
      svg {
        width: 18px;
        height: 18px;
        fill: none;
        stroke: currentcolor;
        stroke-linecap: round;
        stroke-linejoin: round;
        stroke-width: 1.8;
      }
      .stop-icon,
      button[data-loading="true"] .reload-icon {
        display: none;
      }
      button[data-loading="true"] .stop-icon {
        display: inline;
      }
      .address-form {
        min-width: 0;
      }
      .omnibox {
        display: grid;
        grid-template-columns: 16px minmax(0, 1fr);
        align-items: center;
        gap: 9px;
        height: 32px;
        padding: 0 14px;
        background: #10151c;
        border: 1px solid #2c333f;
        border-radius: 999px;
        box-shadow: inset 0 1px 2px rgb(0 0 0 / 28%);
        transition:
          background-color 140ms ease,
          border-color 140ms ease,
          box-shadow 140ms ease;
      }
      .omnibox:hover:not(:focus-within) {
        background: #141a23;
        border-color: #3a4351;
      }
      .omnibox:focus-within {
        background: #1a212c;
        border-color: #48566d;
        box-shadow: 0 1px 4px rgb(0 0 0 / 30%);
      }
      .omnibox-icon {
        width: 16px;
        height: 16px;
        color: #5d6879;
        stroke-width: 1.5;
        transition: color 140ms ease;
      }
      .omnibox:focus-within .omnibox-icon {
        color: #a3aebf;
      }
      input {
        width: 100%;
        min-width: 0;
        height: 100%;
        padding: 0;
        font-family: var(--font-mono);
        font-size: 0.76rem;
        letter-spacing: -0.01em;
        color: #dee4ed;
        text-overflow: ellipsis;
        background: transparent;
        border: 0;
        outline: none;
        caret-color: #79a4ff;
      }
      input::placeholder {
        color: rgb(105 116 134 / 88%);
        font-family: var(--font-sans);
        font-size: 0.8rem;
        letter-spacing: -0.005em;
      }
      .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }
      @media (max-width: 580px) {
        :host {
          gap: 6px;
          min-height: 42px;
          padding: 5px 7px 6px;
        }
        button {
          width: 27px;
          height: 30px;
        }
        .omnibox {
          grid-template-columns: 14px minmax(0, 1fr);
          gap: 7px;
          padding-inline: 10px;
        }
        .omnibox-icon {
          width: 14px;
          height: 14px;
        }
        input {
          font-size: 0.72rem;
        }
        input::placeholder {
          font-size: 0.76rem;
        }
      }
    `,
  ];
  @property({ attribute: false })
  panelId!: string;
  @property({ attribute: false })
  address!: string;
  @property({ attribute: false })
  navigation: NavigationState | undefined = undefined;
  @property({ attribute: false })
  hasActiveTab!: boolean;
  protected get looksLikeUrl() {
    return isAddress(this.address);
  }
  private get addressInput(): HTMLInputElement | undefined {
    return (
      this.renderRoot.querySelector<HTMLInputElement>('[data-ref="addressInput"]') ?? undefined
    );
  }
  focusAddress(): void {
    this.addressInput?.focus();
  }
  protected render() {
    return html`
      <nav aria-label="Page navigation" class=${classMap({ "navigation-controls": true })}>
        <button
          type="button"
          aria-label="Back"
          ?disabled=${!this.navigation?.canGoBack}
          @click=${(event: MouseEvent) => {
            this.dispatchEvent(
              new CustomEvent("back", { detail: undefined, bubbles: true, composed: true }),
            );
          }}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M16.3 10H3.7"></path>
            <path d="m8.7 15-5-5 5-5"></path>
          </svg>
        </button>
        <button
          type="button"
          aria-label="Forward"
          ?disabled=${!this.navigation?.canGoForward}
          @click=${(event: MouseEvent) => {
            this.dispatchEvent(
              new CustomEvent("forward", { detail: undefined, bubbles: true, composed: true }),
            );
          }}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M3.7 10h12.6"></path>
            <path d="m11.3 5 5 5-5 5"></path>
          </svg>
        </button>
        <button
          type="button"
          ?disabled=${!this.hasActiveTab}
          data-loading=${this.navigation?.loading ?? false}
          aria-label=${this.navigation?.loading ? "Stop loading" : "Reload"}
          @click=${(event: MouseEvent) => {
            this.dispatchEvent(
              new CustomEvent("reload-or-stop", {
                detail: undefined,
                bubbles: true,
                composed: true,
              }),
            );
          }}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true" class=${classMap({ "reload-icon": true })}>
            <path d="M16.5 10a6.5 6.5 0 1 1-2.15-4.83"></path>
            <path d="M16.5 3.5v4.3h-4.3"></path>
          </svg>
          <svg viewBox="0 0 20 20" aria-hidden="true" class=${classMap({ "stop-icon": true })}>
            <path d="m5.5 5.5 9 9M14.5 5.5l-9 9"></path>
          </svg>
        </button>
      </nav>
      <form
        class=${classMap({ "address-form": true })}
        @submit=${(event: SubmitEvent) => {
          event.preventDefault();
          this.dispatchEvent(
            new CustomEvent("navigate", { detail: undefined, bubbles: true, composed: true }),
          );
        }}
      >
        <label .for=${this.panelId + "-url"} class=${classMap({ "visually-hidden": true })}
          >Search or enter address</label
        >
        <div class=${classMap({ omnibox: true })}>
          ${
            this.looksLikeUrl
              ? html`
                  <svg
                    viewBox="0 0 20 20"
                    aria-hidden="true"
                    class=${classMap({ "omnibox-icon": true })}
                  >
                    <circle cx="10" cy="10" r="6.75"></circle>
                    <path
                      d="M3.25 10h13.5M10 3.25c1.8 1.9 2.7 4.15 2.7 6.75S11.8 14.85 10 16.75c-1.8-1.9-2.7-4.15-2.7-6.75S8.2 5.15 10 3.25Z"
                    ></path>
                  </svg>
                `
              : html`
                  <svg
                    viewBox="0 0 20 20"
                    aria-hidden="true"
                    class=${classMap({ "omnibox-icon": true })}
                  >
                    <circle cx="8.75" cy="8.75" r="5.25"></circle>
                    <path d="m12.75 12.75 3.75 3.75"></path>
                  </svg>
                `
          }<input
            name="url"
            type="text"
            inputmode="search"
            placeholder="Search DuckDuckGo or enter address"
            autocomplete="off"
            spellcheck="false"
            data-ref="addressInput"
            .id=${this.panelId + "-url"}
            .value=${live(this.address)}
            @input=${(event: InputEvent) => {
              this.dispatchEvent(
                new CustomEvent("address-change", {
                  detail: (event.target as any).value,
                  bubbles: true,
                  composed: true,
                }),
              );
            }}
          />
        </div>
      </form>
    `;
  }
}
customElements.define("app-browser-navigation-bar", BrowserNavigationBar);
