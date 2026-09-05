import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { AdminStatusPill } from "./admin-status-pill";

/** One labelled line of a card. `id` renders the value as an identifier. */
export type AdminFact = {
  readonly label: string;
  readonly value: string;
  readonly full?: string;
  readonly id?: boolean;
};

/**
 * The shape every resource in the panel takes: an identifier, its state, a
 * short column of facts, and the actions it accepts.
 */
@Component({
  selector: "app-admin-card",
  imports: [AdminStatusPill],
  template: `
    <article [class.is-busy]="busy()">
      <header>
        <span class="identifier" [attr.title]="full() ?? null">{{ heading() }}</span>
        <app-admin-status-pill [status]="status()" />
      </header>

      <dl>
        @for (fact of facts(); track fact.label) {
          <div>
            <dt>{{ fact.label }}</dt>
            <dd [class.identifier]="fact.id" [attr.title]="fact.full ?? null">{{ fact.value }}</dd>
          </div>
        }
      </dl>

      <footer><ng-content /></footer>
    </article>
  `,
  styles: `
    :host {
      display: block;
    }
    article {
      display: grid;
      gap: 12px;
      height: 100%;
      padding: 13px 14px 12px;
      background: var(--admin-surface);
      border: 1px solid var(--admin-line);
      border-radius: var(--admin-radius);
      grid-template-rows: auto 1fr auto;
      transition:
        border-color 140ms ease,
        opacity 140ms ease;
    }
    article:hover {
      border-color: var(--admin-line-strong);
    }
    article.is-busy {
      opacity: 0.5;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .identifier {
      overflow: hidden;
      color: var(--admin-text);
      font-family: var(--font-mono);
      font-size: 0.74rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    dl {
      display: grid;
      gap: 5px;
      margin: 0;
    }
    dl div {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
    }
    dt {
      color: var(--admin-text-dim);
      font-size: 0.69rem;
    }
    dd {
      margin: 0;
      overflow: hidden;
      color: var(--admin-text-soft);
      font-size: 0.7rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    dd.identifier {
      font-size: 0.68rem;
    }
    footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 6px;
      padding-top: 11px;
      border-top: 1px solid var(--admin-line);
    }
    @media (prefers-reduced-motion: reduce) {
      article {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminCard {
  readonly heading = input.required<string>();
  readonly status = input.required<string>();
  readonly facts = input.required<readonly AdminFact[]>();
  /** The untruncated identifier, kept for the tooltip. */
  readonly full = input<string>();
  readonly busy = input(false);
}
