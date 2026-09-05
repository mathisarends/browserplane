import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  untracked,
} from "@angular/core";
import { AdminAction } from "./admin-action";
import { AdminBrowserGrid } from "./admin-browser-grid";
import { AdminConsole } from "../services/admin-console";
import { AdminNotice } from "./admin-notice";
import { AdminSessionGrid } from "./admin-session-grid";
import { AdminSnapshotList } from "./admin-snapshot-list";
import { AdminStatStrip } from "./admin-stat-strip";
import { clockTime } from "../services/format";

/** The pool moves without us, so a visible panel keeps pulling. */
const POLL_INTERVAL_MS = 5000;

@Component({
  selector: "app-admin-panel",
  imports: [
    AdminAction,
    AdminBrowserGrid,
    AdminNotice,
    AdminSessionGrid,
    AdminSnapshotList,
    AdminStatStrip,
  ],
  template: `
    <div class="admin">
      <header>
        <hgroup>
          <h1>Browser infrastructure</h1>
          <p>Every provisioned browser and the sessions on it — the state, not a live picture.</p>
        </hgroup>

        <div class="controls">
          @if (updatedAt(); as stamp) {
            <small>Updated {{ stamp }}</small>
          }
          <button appAdminAction [disabled]="console.loading()" (click)="console.refresh()">
            @if (console.loading()) {
              <i class="spinner" aria-hidden="true"></i>
            }
            Refresh
          </button>
        </div>
      </header>

      <app-admin-notice />
      <app-admin-stat-strip />
      <app-admin-browser-grid />
      <app-admin-session-grid />
      <app-admin-snapshot-list />
    </div>
  `,
  styles: `
    :host {
      /* One palette for the whole panel; every child inherits these. */
      --admin-surface: #0e1117;
      --admin-raised: #171b22;
      --admin-hover: #1f242c;
      --admin-line: #1e242d;
      --admin-line-strong: #2b323c;
      --admin-line-bright: #3c434f;
      --admin-text: #e6eaf1;
      --admin-text-soft: #b3bac5;
      --admin-text-dim: #6e757f;
      --admin-text-faint: #565c65;
      --admin-free: #77bb8a;
      --admin-busy: #d3a95f;
      --admin-bad: #d5837a;
      --admin-focus: #79a4ff;
      --admin-radius: 12px;

      display: block;
    }
    .admin {
      display: grid;
      gap: clamp(16px, 1.8vw, 24px);
      width: min(100%, 1180px);
      margin-inline: auto;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    hgroup {
      display: grid;
      gap: 4px;
      min-width: 0;
      margin: 0;
    }
    h1 {
      margin: 0;
      color: var(--admin-text);
      font-size: 1rem;
      font-weight: 650;
      letter-spacing: -0.02em;
    }
    hgroup p {
      margin: 0;
      color: var(--admin-text-dim);
      font-size: 0.73rem;
      line-height: 1.5;
    }
    .controls {
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }
    .controls small {
      color: var(--admin-text-faint);
      font-family: var(--font-mono);
      font-size: 0.65rem;
      white-space: nowrap;
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
      .spinner {
        animation-duration: 1.6s;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminPanel {
  /** The panel stays mounted behind the other tabs; only a visible one polls. */
  readonly active = input(false);

  protected readonly console = inject(AdminConsole);
  protected readonly updatedAt = computed(() => {
    const refreshed = this.console.refreshedAt();
    return refreshed && clockTime(refreshed);
  });

  constructor() {
    effect((onCleanup) => {
      if (!this.active()) return;
      const poll = () => untracked(() => this.console.refresh());
      void poll();
      const timer = setInterval(poll, POLL_INTERVAL_MS);
      onCleanup(() => clearInterval(timer));
    });
  }
}
