import { SignalWatcher } from "@lit-labs/signals";
import { css, html, LitElement, nothing } from "lit";
import { property } from "lit/decorators.js";
export class AdminSection extends SignalWatcher(LitElement) {
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
      header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        padding-bottom: 9px;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--admin-line);
      }
      h2 {
        margin: 0;
        color: var(--admin-text);
        font-size: 0.79rem;
        font-weight: 650;
        letter-spacing: -0.01em;
      }
      small {
        color: var(--admin-text-dim);
        font-family: var(--font-mono);
        font-size: 0.65rem;
        white-space: nowrap;
      }
    `,
  ];
  @property({ attribute: false })
  heading!: string;
  @property({ attribute: false })
  meta: string | undefined = undefined;
  protected render() {
    return html`
      <section aria-label=${this.heading}>
        <header>
          <h2>${this.heading}</h2>
          ${((summary) => (summary ? html` <small>${summary}</small> ` : nothing))(this.meta)}
        </header>
        <slot></slot>
      </section>
    `;
  }
}
customElements.define("app-admin-section", AdminSection);
