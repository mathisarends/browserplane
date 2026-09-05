import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import type { BrowserStateSnapshotResponse } from "@browsertunnel/backend-client";
import { AdminConsole } from "../services/admin-console";
import { AdminSection } from "./admin-section";
import { relativeTime } from "../services/format";

type SnapshotRow = {
  readonly id: string;
  readonly name: string;
  readonly source: string;
  readonly tabs: string;
  readonly age: string;
};

/** Snapshots carry no actions yet, so they stay a list rather than cards. */
@Component({
  selector: "app-admin-snapshot-list",
  imports: [AdminSection],
  template: `
    <app-admin-section heading="Saved browser states" [meta]="meta()">
      <ul>
        @for (row of rows(); track row.id) {
          <li>
            <span class="name">{{ row.name }}</span>
            <span class="source" [title]="row.source">{{ row.source }}</span>
            <span class="tabs">{{ row.tabs }}</span>
            <span class="age">{{ row.age }}</span>
          </li>
        } @empty {
          <li class="empty">Nothing has been captured yet.</li>
        }
      </ul>
    </app-admin-section>
  `,
  styles: `
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
      grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) auto auto;
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
    .source,
    .tabs,
    .age {
      color: var(--admin-text-dim);
      font-family: var(--font-mono);
      font-size: 0.65rem;
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
      color: var(--admin-text-dim);
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
  private readonly console = inject(AdminConsole);

  protected readonly meta = computed(() => `${this.console.snapshots().length} snapshots`);
  protected readonly rows = computed<readonly SnapshotRow[]>(() =>
    this.console.snapshots().map((snapshot) => ({
      id: snapshot.id,
      name: snapshot.name,
      source: snapshot.source_browser,
      tabs: `${tabCount(snapshot)} tabs`,
      age: relativeTime(snapshot.created_at),
    })),
  );
}

function tabCount(snapshot: BrowserStateSnapshotResponse): number {
  return snapshot.browser_state.tabs?.length ?? 0;
}
