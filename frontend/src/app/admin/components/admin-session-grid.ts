import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { AdminConsole } from "../services/admin-console";
import { AdminSection } from "./admin-section";
import { AdminSessionCard } from "./admin-session-card";

@Component({
  selector: "app-admin-session-grid",
  imports: [AdminSection, AdminSessionCard],
  template: `
    <app-admin-section heading="Sessions" [meta]="meta()">
      <div class="cards">
        @for (session of console.sessions(); track session.id) {
          <app-admin-session-card [session]="session" />
        } @empty {
          <p class="empty">
            {{ console.loaded() ? "No session is open right now." : "Loading sessions…" }}
          </p>
        }
      </div>
    </app-admin-section>
  `,
  styles: `
    :host {
      display: block;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(258px, 1fr));
      gap: 10px;
    }
    .empty {
      grid-column: 1 / -1;
      padding: 26px 16px;
      margin: 0;
      color: var(--admin-text-dim);
      font-size: 0.72rem;
      text-align: center;
      border: 1px dashed var(--admin-line);
      border-radius: var(--admin-radius);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminSessionGrid {
  protected readonly console = inject(AdminConsole);

  protected readonly meta = computed(
    () =>
      `${this.console.activeSessions().length} active · ` +
      `${this.console.suspendedSessions().length} suspended`,
  );
}
