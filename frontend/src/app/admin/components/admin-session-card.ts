import { ChangeDetectionStrategy, Component, computed, inject, input } from "@angular/core";
import type { SessionResponse } from "@browsertunnel/backend-client";
import { AdminAction } from "./admin-action";
import { AdminCard, type AdminFact } from "./admin-card";
import { AdminConsole } from "../services/admin-console";
import { relativeTime, shortId } from "../services/format";

@Component({
  selector: "app-admin-session-card",
  imports: [AdminAction, AdminCard],
  template: `
    <app-admin-card
      [heading]="label()"
      [full]="session().id"
      [status]="session().status"
      [facts]="facts()"
      [busy]="busy()"
    >
      @if (session().status === "active") {
        <button appAdminAction [disabled]="busy()" (click)="console.suspendSession(session().id)">
          Suspend
        </button>
      } @else {
        <button appAdminAction [disabled]="busy()" (click)="console.resumeSession(session().id)">
          Resume
        </button>
      }
      <button appAdminAction [disabled]="busy()" (click)="console.closeSession(session().id)">
        Close
      </button>
    </app-admin-card>
  `,
  styles: `
    :host {
      display: block;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminSessionCard {
  readonly session = input.required<SessionResponse>();

  protected readonly console = inject(AdminConsole);

  protected readonly label = computed(() => shortId(this.session().id));
  protected readonly busy = computed(() => this.console.isBusy(this.session().id));
  protected readonly facts = computed<readonly AdminFact[]>(() => {
    const session = this.session();
    return [
      { label: "Owner", value: shortId(session.owner_id), full: session.owner_id, id: true },
      {
        label: "Browser",
        value: session.browser_id ? shortId(session.browser_id) : "—",
        full: session.browser_id ?? undefined,
        id: true,
      },
      { label: "Opened", value: relativeTime(session.created_at) },
      { label: "Expires", value: session.expires_at ? relativeTime(session.expires_at) : "—" },
    ];
  });
}
