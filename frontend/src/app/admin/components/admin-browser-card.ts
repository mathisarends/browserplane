import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from "@angular/core";
import type { PooledBrowserResponse } from "@browsertunnel/backend-client";
import { AdminAction } from "./admin-action";
import { AdminCard, type AdminFact } from "./admin-card";
import { AdminConsole } from "../services/admin-console";
import { relativeTime, shortId } from "../services/format";

@Component({
  selector: "app-admin-browser-card",
  imports: [AdminAction, AdminCard],
  template: `
    <app-admin-card
      [heading]="label()"
      [full]="browser().id"
      [status]="browser().state"
      [facts]="facts()"
      [busy]="busy()"
    >
      @if (confirming()) {
        <span class="prompt">Release this browser?</span>
        <button appAdminAction (click)="confirming.set(false)">Cancel</button>
        <button appAdminAction tone="danger" [disabled]="busy()" (click)="release()">
          Release
        </button>
      } @else {
        <button appAdminAction [disabled]="busy()" (click)="console.restartBrowser(browser().id)">
          Restart
        </button>
        <button appAdminAction [disabled]="busy()" (click)="confirming.set(true)">Release</button>
      }
    </app-admin-card>
  `,
  styles: `
    :host {
      display: block;
    }
    .prompt {
      margin-right: auto;
      color: var(--admin-text-dim);
      font-size: 0.68rem;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminBrowserCard {
  readonly browser = input.required<PooledBrowserResponse>();

  protected readonly console = inject(AdminConsole);
  /** Releasing removes a live runtime, so it takes a second, deliberate click. */
  protected readonly confirming = signal(false);

  protected readonly label = computed(() => shortId(this.browser().id));
  protected readonly busy = computed(() => this.console.isBusy(this.browser().id));
  protected readonly facts = computed<readonly AdminFact[]>(() => {
    const lease = this.browser().lease;
    return [
      { label: "Provisioned", value: relativeTime(this.browser().created_at) },
      {
        label: "Held by",
        value: lease ? shortId(lease.session_id) : "—",
        full: lease?.session_id,
        id: true,
      },
      {
        label: "Owner",
        value: lease ? shortId(lease.owner_id) : "—",
        full: lease?.owner_id,
        id: true,
      },
      { label: "Lease ends", value: lease ? relativeTime(lease.expires_at) : "—" },
    ];
  });

  protected async release(): Promise<void> {
    this.confirming.set(false);
    await this.console.releaseBrowser(this.browser().id);
  }
}
