import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import type { BrowserStateSnapshotResponse } from "@browsertunnel/backend-client";
import { AdminConsole, short } from "../services/admin-console";
import { relativeTime } from "../services/time";

@Component({
  selector: "app-admin-snapshot-list",
  template: `
    <section aria-labelledby="admin-snapshots-heading">
      <header>
        <h2 id="admin-snapshots-heading">Saved browser states</h2>
        <small>{{ console.snapshots().length }} snapshots</small>
      </header>

      <ul>
        @for (snapshot of console.snapshots(); track snapshot.id) {
          <li>
            <span class="name">{{ snapshot.name }}</span>
            <span class="source" [title]="snapshot.source_browser">
              {{ snapshot.source_browser }}
            </span>
            <span class="tabs">{{ tabCount(snapshot) }} tabs</span>
            <span class="age">{{ since(snapshot.created_at) }}</span>
          </li>
        } @empty {
          <li class="empty">Nothing has been captured yet.</li>
        }
      </ul>
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
    ul {
      max-height: 268px;
      padding: 0;
      margin: 0;
      overflow-y: auto;
      list-style: none;
    }
    li {
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) auto auto;
      gap: 12px;
      align-items: center;
      padding: 10px 16px;
      font-size: 0.72rem;
      border-top: 1px solid #1b212a;
    }
    li:first-child {
      border-top: 0;
    }
    .name {
      overflow: hidden;
      color: #d6dae1;
      font-weight: 600;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .source,
    .tabs,
    .age {
      color: #6c727d;
      font-family: var(--font-mono);
      font-size: 0.66rem;
    }
    .source {
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
      color: #626873;
      text-align: center;
    }
    @media (max-width: 640px) {
      li {
        grid-template-columns: minmax(0, 1fr) auto;
      }
      .source {
        display: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminSnapshotList {
  protected readonly console = inject(AdminConsole);

  protected shortId(id: string): string {
    return short(id);
  }

  protected tabCount(snapshot: BrowserStateSnapshotResponse): number {
    return snapshot.browser_state.tabs?.length ?? 0;
  }

  protected since(timestamp: string): string {
    return relativeTime(timestamp);
  }
}
