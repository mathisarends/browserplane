import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import { adminConsoleContext } from "../../shared/contexts";
import { AdminConsole } from "../services/admin-console";
import { relativeTime } from "../services/format";
import "./admin-section";
type CheckpointRow = {
  readonly id: string;
  readonly profile: string;
  readonly age: string;
};
export class AdminCheckpointList extends SignalWatcher(LitElement) {
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
      ul {
        max-height: 268px;
        padding: 0;
        margin: 0;
        overflow-y: auto;
        list-style: none;
        background: var(--admin-surface);
        border: 1px solid var(--admin-line);
        border-radius: var(--admin-radius);
      }
      li {
        display: grid;
        grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) auto;
        gap: 12px;
        align-items: center;
        padding: 10px 14px;
        font-size: 0.72rem;
        border-top: 1px solid var(--admin-line);
      }
      li:first-child {
        border-top: 0;
      }
      .name {
        overflow: hidden;
        color: var(--admin-text-soft);
        font-weight: 600;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .profile,
      .age {
        color: var(--admin-text-dim);
        font-family: var(--font-mono);
        font-size: 0.65rem;
      }
      .profile {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .age {
        text-align: right;
        white-space: nowrap;
      }
      .empty {
        display: block;
        padding: 26px 16px;
        color: var(--admin-text-dim);
        text-align: center;
      }
      @media (max-width: 640px) {
        li {
          grid-template-columns: minmax(0, 1fr) auto;
        }
        .profile {
          display: none;
        }
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
    return `${this.console.checkpoints.get().length} checkpoints`;
  }
  protected get rows(): readonly CheckpointRow[] {
    return this.console.checkpoints.get().map((checkpoint) => ({
      id: checkpoint.id.slice(0, 8),
      profile: checkpoint.authentication_profile_id ? "with profile" : "without profile",
      age: relativeTime(checkpoint.created_at),
    }));
  }
  protected render() {
    return html`
      <app-admin-section heading="Browser checkpoints" .meta=${this.meta}>
        <ul>
          ${
            this.rows.length
              ? repeat(
                  this.rows,
                  (row, index) => row.id,
                  (row, index) => html`
                    <li>
                      <span class=${classMap({ name: true })}>Checkpoint ${row.id}</span>
                      <span class=${classMap({ profile: true })}>${row.profile}</span>
                      <span class=${classMap({ age: true })}>${row.age}</span>
                    </li>
                  `,
                )
              : html` <li class=${classMap({ empty: true })}>Nothing has been captured yet.</li> `
          }
        </ul>
      </app-admin-section>
    `;
  }
}
customElements.define("app-admin-checkpoint-list", AdminCheckpointList);
