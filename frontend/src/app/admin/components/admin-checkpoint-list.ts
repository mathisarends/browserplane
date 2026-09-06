import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { AdminConsole } from "../services/admin-console";
import { AdminSection } from "./admin-section";
import { relativeTime } from "../services/format";

type CheckpointRow = {
  readonly id: string;
  readonly profile: string;
  readonly age: string;
};

/** Checkpoints carry no admin actions yet, so they stay a compact list. */
@Component({
  selector: "app-admin-checkpoint-list",
  imports: [AdminSection],
  template: `
    <app-admin-section heading="Browser checkpoints" [meta]="meta()">
      <ul>
        @for (row of rows(); track row.id) {
          <li>
            <span class="name">Checkpoint {{ row.id }}</span>
            <span class="profile">{{ row.profile }}</span>
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminCheckpointList {
  private readonly console = inject(AdminConsole);

  protected readonly meta = computed(() => `${this.console.checkpoints().length} checkpoints`);
  protected readonly rows = computed<readonly CheckpointRow[]>(() =>
    this.console.checkpoints().map((checkpoint) => ({
      id: checkpoint.id.slice(0, 8),
      profile: checkpoint.authentication_profile_id ? "with profile" : "without profile",
      age: relativeTime(checkpoint.created_at),
    })),
  );
}
