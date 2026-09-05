import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { AdminBrowserCard } from "./admin-browser-card";
import { AdminConsole } from "../services/admin-console";
import { AdminSection } from "./admin-section";

@Component({
  selector: "app-admin-browser-grid",
  imports: [AdminBrowserCard, AdminSection],
  template: `
    <app-admin-section heading="Browser pool" [meta]="meta()">
      <div class="cards">
        @for (browser of console.browsers(); track browser.id) {
          <app-admin-browser-card [browser]="browser" />
        } @empty {
          <p class="empty">
            {{ console.loaded() ? "No browsers are provisioned." : "Loading the pool…" }}
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
export class AdminBrowserGrid {
  protected readonly console = inject(AdminConsole);

  protected readonly meta = computed(() => {
    const total = this.console.browsers().length;
    return `${this.console.availableBrowsers().length} of ${total} available`;
  });
}
