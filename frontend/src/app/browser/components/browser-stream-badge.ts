import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement, nothing } from "lit";
import { classMap } from "lit/directives/class-map.js";
import { browserSessionContext } from "../../shared/contexts";
import { BrowserSession } from "../services/browser-session";
export class BrowserStreamBadge extends SignalWatcher(LitElement) {
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

      .stream-badge {
        display: flex;
        flex-wrap: wrap;
        gap: 0 12px;
        margin: 0;
        padding: 6px 12px;
        color: #8d9bb2;
        font-size: 12px;
        font-variant-numeric: tabular-nums;
        background: #0d1117;
        border-top: 1px solid #1d2530;
      }

      strong {
        color: #c6d3e6;
        font-weight: 600;
      }

      i {
        align-self: center;
        width: 7px;
        height: 7px;
        background: #f0a63c;
        border-radius: 50%;
      }

      .stream-badge[data-state="complete"] i {
        background: #4ec98a;
      }
    `,
  ];
  private readonly sessionConsumer = new ContextConsumer(this, {
    context: browserSessionContext,
    subscribe: true,
  });
  protected get session(): BrowserSession {
    const value = this.sessionConsumer.value;
    if (!value) throw new Error("Missing BrowserSession provider");
    return value;
  }
  protected get stream() {
    return this.session.stream.dirtyRectangles.get();
  }
  protected get megabytes() {
    return ((this.stream?.bytes ?? 0) / 1048576).toFixed(2);
  }
  protected render() {
    return html` ${((state) =>
      state
        ? html`
            <p
              data-state=${state.complete ? "complete" : "partial"}
              class=${classMap({ "stream-badge": true })}
            >
              <i aria-hidden="true"></i>
              <strong>dirty rectangles</strong>
              <span>${state.coveredTiles}/${state.tiles} tiles</span>
              <span>${state.packets} packets · ${state.patches} patches</span>
              <span>${this.megabytes} MB</span>
              ${state.resyncs ? html` <span>${state.resyncs} resyncs</span> ` : nothing}${
                !state.connected ? html` <span>reconnecting</span> ` : nothing
              }
            </p>
          `
        : nothing)(this.stream)}`;
  }
}
customElements.define("app-browser-stream-badge", BrowserStreamBadge);
