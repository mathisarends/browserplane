import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  OnDestroy,
} from "@angular/core";
import { AdminBrowserTable } from "./admin-browser-table";
import { AdminConsole } from "../services/admin-console";
import { AdminSessionTable } from "./admin-session-table";
import { AdminSnapshotList } from "./admin-snapshot-list";
import { AdminStatStrip } from "./admin-stat-strip";
import { clockTime } from "../services/time";

/** The pool moves without us, so a visible panel keeps pulling. */
const POLL_INTERVAL_MS = 5000;

@Component({
  selector: "app-admin-panel",
  imports: [AdminBrowserTable, AdminSessionTable, AdminSnapshotList, AdminStatStrip],
  template: `
    <section class="admin" aria-label="Browser pool administration">
      <header class="admin-header">
        <span class="title">
          <strong>Browser infrastructure</strong>
          <small>
            Every provisioned browser and the sessions on it — no live picture, just the state.
          </small>
        </span>

        <span class="controls">
          @if (console.refreshedAt(); as refreshed) {
            <small class="stamp">Updated {{ time(refreshed) }}</small>
          }
          <button type="button" [disabled]="console.loading()" (click)="console.refresh()">
            @if (console.loading()) {
              <i class="spinner" aria-hidden="true"></i>
            }
            Refresh
          </button>
        </span>
      </header>

      @if (console.notice(); as notice) {
        <div class="notice" [attr.data-tone]="notice.tone" role="status">
          <i aria-hidden="true"></i>
          <span>{{ notice.text }}</span>
          <button type="button" aria-label="Dismiss" (click)="console.dismissNotice()">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="m4.5 4.5 7 7M11.5 4.5l-7 7" />
            </svg>
          </button>
        </div>
      }

      <app-admin-stat-strip />
      <app-admin-browser-table [loaded]="loaded()" />
      <app-admin-session-table [loaded]="loaded()" />
      <app-admin-snapshot-list />
    </section>
  `,
  styles: `
    :host {
      display: block;
    }
    .admin {
      display: grid;
      gap: clamp(12px, 1.4vw, 18px);
      width: min(100%, 1280px);
      margin-inline: auto;
    }
    .admin-header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    .title {
      display: grid;
      gap: 5px;
      min-width: 0;
    }
    .title strong {
      color: #e9edf3;
      font-size: 0.98rem;
      font-weight: 650;
      letter-spacing: -0.015em;
    }
    .title small {
      color: #6c727d;
      font-size: 0.72rem;
      line-height: 1.5;
    }
    .controls {
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }
    .stamp {
      color: #5e646e;
      font-family: var(--font-mono);
      font-size: 0.66rem;
    }
    .controls button {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      min-height: 30px;
      padding: 0 13px;
      color: #c8ccd3;
      font-size: 0.72rem;
      font-weight: 600;
      background: #1b1e24;
      border: 1px solid #2e323a;
      border-radius: 8px;
      cursor: pointer;
      transition:
        color 130ms ease,
        background-color 130ms ease,
        border-color 130ms ease;
    }
    .controls button:hover:not(:disabled) {
      color: #f1f2f4;
      background: #252931;
      border-color: #3d424b;
    }
    .controls button:disabled {
      color: #5b616a;
      cursor: default;
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    .notice {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 9px 10px 9px 13px;
      color: #7fb98f;
      font-size: 0.73rem;
      background: rgb(88 168 110 / 8%);
      border: 1px solid rgb(88 168 110 / 24%);
      border-radius: 10px;
    }
    .notice[data-tone="error"] {
      color: #d5837a;
      background: rgb(203 105 98 / 8%);
      border-color: rgb(203 105 98 / 26%);
    }
    .notice > i {
      flex: none;
      width: 6px;
      height: 6px;
      background: currentcolor;
      border-radius: 50%;
    }
    .notice span {
      flex: 1;
      min-width: 0;
    }
    .notice button {
      display: grid;
      place-items: center;
      flex: none;
      width: 22px;
      height: 22px;
      padding: 0;
      color: inherit;
      background: transparent;
      border: 0;
      border-radius: 6px;
      cursor: pointer;
    }
    .notice button:hover {
      background: rgb(255 255 255 / 7%);
    }
    .notice svg {
      width: 12px;
      height: 12px;
      fill: none;
      stroke: currentcolor;
      stroke-linecap: round;
      stroke-width: 1.6;
    }
    .spinner {
      width: 10px;
      height: 10px;
      border: 1.5px solid currentcolor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 650ms linear infinite;
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .controls button {
        transition: none;
      }
      .spinner {
        animation-duration: 1.6s;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminPanel implements OnDestroy {
  /** The panel stays mounted behind the other tabs; only a visible one polls. */
  readonly active = input(false);
  protected readonly console = inject(AdminConsole);
  private timer?: ReturnType<typeof setInterval>;

  constructor() {
    effect(() => (this.active() ? this.startPolling() : this.stopPolling()));
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  protected loaded(): boolean {
    return this.console.refreshedAt() !== undefined;
  }

  protected time(date: Date): string {
    return clockTime(date);
  }

  private startPolling(): void {
    if (this.timer) return;
    void this.console.refresh();
    this.timer = setInterval(() => void this.console.refresh(), POLL_INTERVAL_MS);
  }

  private stopPolling(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }
}
