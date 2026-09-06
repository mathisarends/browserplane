import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { AdminConsole } from "../services/admin-console";

type Tone = "plain" | "free" | "busy" | "bad";
type Stat = { readonly label: string; readonly value: number; readonly tone: Tone };

@Component({
  selector: "app-admin-stat-strip",
  template: `
    <dl aria-label="Pool summary">
      @for (stat of stats(); track stat.label) {
        <div [attr.data-tone]="stat.tone">
          <dt>{{ stat.label }}</dt>
          <dd>{{ stat.value }}</dd>
        </div>
      }
    </dl>
  `,
  styles: `
    :host {
      display: block;
    }
    dl {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
      gap: 1px;
      margin: 0;
      overflow: hidden;
      background: var(--admin-line);
      border: 1px solid var(--admin-line);
      border-radius: var(--admin-radius);
    }
    div {
      display: flex;
      align-items: baseline;
      gap: 8px;
      padding: 11px 14px;
      background: var(--admin-surface);
    }
    /* The count leads, the label follows; the markup stays dt-then-dd. */
    dd {
      order: -1;
      margin: 0;
      color: var(--admin-text);
      font-size: 1rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.02em;
      line-height: 1;
    }
    dt {
      color: var(--admin-text-dim);
      font-size: 0.68rem;
      white-space: nowrap;
    }
    div[data-tone="free"] dd {
      color: var(--admin-free);
    }
    div[data-tone="busy"] dd {
      color: var(--admin-busy);
    }
    div[data-tone="bad"] dd {
      color: var(--admin-bad);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminStatStrip {
  private readonly console = inject(AdminConsole);

  protected readonly stats = computed<readonly Stat[]>(() => [
    { label: "Browsers", value: this.console.browsers().length, tone: "plain" },
    { label: "Available", value: this.console.availableBrowsers().length, tone: "free" },
    { label: "Active", value: this.console.activeSessions().length, tone: "busy" },
    { label: "Suspended", value: this.console.suspendedSessions().length, tone: "plain" },
    { label: "Offline", value: this.console.offlineBrowsers().length, tone: "bad" },
    { label: "Checkpoints", value: this.console.checkpoints().length, tone: "plain" },
  ]);
}
