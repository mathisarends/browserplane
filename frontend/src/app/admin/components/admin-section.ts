import { ChangeDetectionStrategy, Component, input } from "@angular/core";

/** A titled band of the panel: a hairline heading, then whatever it holds. */
@Component({
  selector: "app-admin-section",
  template: `
    <section [attr.aria-label]="heading()">
      <header>
        <h2>{{ heading() }}</h2>
        @if (meta(); as summary) {
          <small>{{ summary }}</small>
        }
      </header>
      <ng-content />
    </section>
  `,
  styles: `
    :host {
      display: block;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      padding-bottom: 9px;
      margin-bottom: 12px;
      border-bottom: 1px solid var(--admin-line);
    }
    h2 {
      margin: 0;
      color: var(--admin-text);
      font-size: 0.79rem;
      font-weight: 650;
      letter-spacing: -0.01em;
    }
    small {
      color: var(--admin-text-dim);
      font-family: var(--font-mono);
      font-size: 0.65rem;
      white-space: nowrap;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminSection {
  readonly heading = input.required<string>();
  readonly meta = input<string>();
}
