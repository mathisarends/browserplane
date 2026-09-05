import { ChangeDetectionStrategy, Component, inject, input } from "@angular/core";
import { AdminConsole, short } from "../services/admin-console";
import { AdminStatusPill } from "./admin-status-pill";
import { relativeTime } from "../services/time";

@Component({
  selector: "app-admin-session-table",
  imports: [AdminStatusPill],
  template: `
    <section aria-labelledby="admin-sessions-heading">
      <header>
        <h2 id="admin-sessions-heading">Sessions</h2>
        <small>
          {{ console.activeSessions().length }} active ·
          {{ console.suspendedSessions().length }} suspended
        </small>
      </header>

      <div class="scroller">
        <table>
          <thead>
            <tr>
              <th scope="col">Session</th>
              <th scope="col">Status</th>
              <th scope="col">Owner</th>
              <th scope="col">Browser</th>
              <th scope="col">Opened</th>
              <th scope="col">Expires</th>
              <th scope="col"><span class="visually-hidden">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            @for (session of console.sessions(); track session.id) {
              <tr [class.is-busy]="console.isBusy(session.id)">
                <td class="identifier" [title]="session.id">{{ shortId(session.id) }}</td>
                <td><app-admin-status-pill [status]="session.status" /></td>
                <td class="identifier muted" [title]="session.owner_id">
                  {{ shortId(session.owner_id) }}
                </td>
                <td class="identifier muted" [title]="session.browser_id ?? ''">
                  {{ session.browser_id ? shortId(session.browser_id) : "—" }}
                </td>
                <td class="muted">{{ since(session.created_at) }}</td>
                <td class="muted">{{ since(session.expires_at) }}</td>
                <td class="actions">
                  @if (session.status === "active") {
                    <button
                      type="button"
                      [disabled]="console.isBusy(session.id)"
                      (click)="console.suspendSession(session.id)"
                    >
                      Suspend
                    </button>
                  } @else {
                    <button
                      type="button"
                      [disabled]="console.isBusy(session.id)"
                      (click)="console.resumeSession(session.id)"
                    >
                      Resume
                    </button>
                  }
                  <button
                    type="button"
                    [disabled]="console.isBusy(session.id)"
                    (click)="console.closeSession(session.id)"
                  >
                    Close
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td class="empty" colspan="7">
                  {{ loaded() ? "No session is open right now." : "Loading sessions…" }}
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
  `,
  styles: `
    :host {
      display: block;
    }
    section {
      overflow: hidden;
      background: #0e1117;
      border: 1px solid #222932;
      border-radius: 14px;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      padding: 13px 16px;
      border-bottom: 1px solid #1e242d;
    }
    h2 {
      margin: 0;
      color: #e4e8ee;
      font-size: 0.82rem;
      font-weight: 650;
      letter-spacing: -0.01em;
    }
    header small {
      color: #626873;
      font-family: var(--font-mono);
      font-size: 0.66rem;
    }
    .scroller {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.72rem;
    }
    th {
      padding: 9px 16px;
      color: #616772;
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 500;
      letter-spacing: 0.04em;
      text-align: left;
      text-transform: uppercase;
      white-space: nowrap;
      background: #101419;
    }
    td {
      padding: 11px 16px;
      color: #c4c9d2;
      vertical-align: middle;
      white-space: nowrap;
      border-top: 1px solid #1b212a;
    }
    tr.is-busy td {
      opacity: 0.55;
    }
    .identifier {
      font-family: var(--font-mono);
      font-size: 0.7rem;
    }
    .muted {
      color: #6c727d;
    }
    .empty {
      padding: 26px 16px;
      color: #626873;
      text-align: center;
    }
    .actions {
      display: flex;
      gap: 6px;
      justify-content: flex-end;
    }
    button {
      min-height: 27px;
      padding: 0 11px;
      color: #c2c5cb;
      font-size: 0.69rem;
      font-weight: 600;
      background: #1b1e24;
      border: 1px solid #2e323a;
      border-radius: 7px;
      cursor: pointer;
      transition:
        color 130ms ease,
        background-color 130ms ease,
        border-color 130ms ease;
    }
    button:hover:not(:disabled) {
      color: #f1f2f4;
      background: #252931;
      border-color: #3d424b;
    }
    button:disabled {
      color: #5b616a;
      cursor: default;
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
    }
    @media (prefers-reduced-motion: reduce) {
      button {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminSessionTable {
  readonly loaded = input(false);
  protected readonly console = inject(AdminConsole);

  protected shortId(id: string): string {
    return short(id);
  }

  protected since(timestamp: string): string {
    return relativeTime(timestamp);
  }
}
