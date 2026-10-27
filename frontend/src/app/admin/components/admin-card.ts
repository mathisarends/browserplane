import { SignalWatcher } from "@lit-labs/signals";
import { css, html, LitElement } from "lit";
import { property } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import "./admin-status-pill";
export type AdminFact = {
  readonly label: string;
  readonly value: string;
  readonly full?: string;
  readonly id?: boolean;
};
export class AdminCard extends SignalWatcher(LitElement) {
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
      article {
        display: grid;
        gap: 12px;
        height: 100%;
        padding: 13px 14px 12px;
        background: var(--admin-surface);
        border: 1px solid var(--admin-line);
        border-radius: var(--admin-radius);
        grid-template-rows: auto 1fr auto;
        transition:
          border-color 140ms ease,
          opacity 140ms ease;
      }
      article:hover {
        border-color: var(--admin-line-strong);
      }
      article.is-busy {
        opacity: 0.5;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }
      .identifier {
        overflow: hidden;
        color: var(--admin-text);
        font-family: var(--font-mono);
        font-size: 0.74rem;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      dl {
        display: grid;
        gap: 5px;
        margin: 0;
      }
      dl div {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
      }
      dt {
        color: var(--admin-text-dim);
        font-size: 0.69rem;
      }
      dd {
        margin: 0;
        overflow: hidden;
        color: var(--admin-text-soft);
        font-size: 0.7rem;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      dd.identifier {
        font-size: 0.68rem;
      }
      footer {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
        padding-top: 11px;
        border-top: 1px solid var(--admin-line);
      }
      @media (prefers-reduced-motion: reduce) {
        article {
          transition: none;
        }
      }
    `,
  ];
  @property({ attribute: false })
  heading!: string;
  @property({ attribute: false })
  status!: string;
  @property({ attribute: false })
  facts!: readonly AdminFact[];
  @property({ attribute: false })
  full: string | undefined = undefined;
  @property({ attribute: false })
  busy: boolean = false;
  protected render() {
    return html`
      <article class=${classMap({ "is-busy": Boolean(this.busy) })}>
        <header>
          <span title=${this.full ?? null} class=${classMap({ identifier: true })}
            >${this.heading}</span
          >
          <app-admin-status-pill .status=${this.status}></app-admin-status-pill>
        </header>

        <dl>
          ${repeat(
            this.facts,
            (fact, index) => fact.label,
            (fact, index) => html`
              <div>
                <dt>${fact.label}</dt>
                <dd title=${fact.full ?? null} class=${classMap({ identifier: Boolean(fact.id) })}>
                  ${fact.value}
                </dd>
              </div>
            `,
          )}
        </dl>

        <footer><slot></slot></footer>
      </article>
    `;
  }
}
customElements.define("app-admin-card", AdminCard);
