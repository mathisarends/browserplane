import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { AdminConsole } from "../services/admin-console";

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
      grid-template-columns: repeat(auto-fit, minmax(126px, 1fr));
      gap: 10px;
      margin: 0;
    }
    div {
      display: grid;
      gap: 6px;
      padding: 13px 15px;
      background: #11151c;
      border: 1px solid #222932;
      border-radius: 12px;
    }
    dt {
      color: #6a707b;
      font-family: var(--font-mono);
      font-size: 0.63rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    dd {
      margin: 0;
      color: #e7eaf0;
      font-size: 1.4rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.02em;
      line-height: 1;
    }
    div[data-tone="free"] dd {
      color: #7fc292;
    }
    div[data-tone="busy"] dd {
      color: #d9b16a;
    }
    div[data-tone="bad"] dd {
      color: #d5837a;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminStatStrip {
  private readonly console = inject(AdminConsole);

  protected readonly stats = computed(() => [
    { label: "Browsers", value: this.console.browsers().length, tone: "plain" },
    { label: "Available", value: this.console.availableBrowsers().length, tone: "free" },
    { label: "Active", value: this.console.activeSessions().length, tone: "busy" },
    { label: "Suspended", value: this.console.suspendedSessions().length, tone: "plain" },
    { label: "Offline", value: this.console.offlineBrowsers().length, tone: "bad" },
    { label: "Snapshots", value: this.console.snapshots().length, tone: "plain" },
  ]);
}
