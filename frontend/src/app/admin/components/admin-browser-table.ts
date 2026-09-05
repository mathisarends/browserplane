import { ChangeDetectionStrategy, Component, inject, input, signal } from "@angular/core";
import { AdminConsole, short } from "../services/admin-console";
import { AdminStatusPill } from "./admin-status-pill";
import { relativeTime } from "../services/time";

@Component({
  selector: "app-admin-browser-table",
  imports: [AdminStatusPill],
  template: `
    <section aria-labelledby="admin-browsers-heading">
      <header>
        <h2 id="admin-browsers-heading">Browser pool</h2>
        <small>{{ console.browsers().length }} provisioned slots</small>
      </header>

      <div class="scroller">
        <table>
          <thead>
            <tr>
              <th scope="col">Browser</th>
              <th scope="col">State</th>
              <th scope="col">Provisioned</th>
              <th scope="col">Held by</th>
              <th scope="col">Lease ends</th>
              <th scope="col"><span class="visually-hidden">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            @for (browser of console.browsers(); track browser.id) {
              <tr [class.is-busy]="console.isBusy(browser.id)">
                <td class="identifier" [title]="browser.id">{{ shortId(browser.id) }}</td>
                <td><app-admin-status-pill [status]="browser.state" /></td>
                <td class="muted">{{ since(browser.created_at) }}</td>
                <td>
                  @if (browser.lease; as lease) {
                    <span class="holder">
                      <span class="identifier" [title]="lease.session_id">{{
                        shortId(lease.session_id)
                      }}</span>
                      <small [title]="lease.owner_id">owner {{ shortId(lease.owner_id) }}</small>
                    </span>
                  } @else {
                    <span class="muted">—</span>
                  }
                </td>
                <td class="muted">
                  {{ browser.lease ? since(browser.lease.expires_at) : "—" }}
                </td>
                <td class="actions">
                  @if (confirming() === browser.id) {
                    <button
                      type="button"
                      class="danger"
                      [disabled]="console.isBusy(browser.id)"
                      (click)="destroy(browser.id)"
                    >
                      Confirm
                    </button>
                    <button type="button" (click)="confirming.set(undefined)">Cancel</button>
                  } @else {
                    <button
                      type="button"
                      [disabled]="console.isBusy(browser.id)"
                      (click)="console.restartBrowser(browser.id)"
                    >
                      Restart
                    </button>
                    <button
                      type="button"
                      [disabled]="console.isBusy(browser.id)"
                      (click)="confirming.set(browser.id)"
                    >
                      Destroy
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td class="empty" colspan="6">
                  {{ loaded() ? "No browsers are provisioned." : "Loading the pool…" }}
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
      color: #d3d8e0;
      font-family: var(--font-mono);
      font-size: 0.7rem;
    }
    .muted {
      color: #6c727d;
    }
    .holder {
      display: grid;
      gap: 2px;
    }
    .holder small {
      color: #626873;
      font-family: var(--font-mono);
      font-size: 0.62rem;
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
    button.danger {
      color: #f0d2ce;
      background: #47231f;
      border-color: #6a322c;
    }
    button.danger:hover:not(:disabled) {
      color: #fff;
      background: #592b25;
      border-color: #813b33;
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
export class AdminBrowserTable {
  readonly loaded = input(false);
  protected readonly console = inject(AdminConsole);
  /** Destroying kills a live browser, so it takes a second, deliberate click. */
  protected readonly confirming = signal<string | undefined>(undefined);

  protected async destroy(browserId: string): Promise<void> {
    this.confirming.set(undefined);
    await this.console.destroyBrowser(browserId);
  }

  protected shortId(id: string): string {
    return short(id);
  }

  protected since(timestamp: string): string {
    return relativeTime(timestamp);
  }
}
