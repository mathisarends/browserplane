import { ChangeDetectionStrategy, Component, input } from "@angular/core";

/** Quiet by default: an operator's eye should land on state, not on buttons. */
export type ActionTone = "quiet" | "danger";

/**
 * The one button of the admin view, worn by a real `<button>`.
 *
 * Attaching to the element instead of wrapping it keeps `disabled`, `click`
 * and focus native, so every call site stays plain HTML.
 */
@Component({
  selector: "button[appAdminAction]",
  template: `<ng-content />`,
  host: { type: "button", "[attr.data-tone]": "tone()" },
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 27px;
      padding: 0 11px;
      color: var(--admin-text-soft);
      font-size: 0.7rem;
      font-weight: 600;
      background: var(--admin-raised);
      border: 1px solid var(--admin-line-strong);
      border-radius: 8px;
      cursor: pointer;
      transition:
        color 130ms ease,
        background-color 130ms ease,
        border-color 130ms ease;
    }
    :host(:hover:not(:disabled)) {
      color: var(--admin-text);
      background: var(--admin-hover);
      border-color: var(--admin-line-bright);
    }
    :host(:disabled) {
      color: var(--admin-text-faint);
      cursor: default;
    }
    :host(:focus-visible) {
      outline: 2px solid var(--admin-focus);
      outline-offset: 1px;
    }
    :host([data-tone="danger"]) {
      color: var(--admin-bad);
      border-color: rgb(203 105 98 / 30%);
    }
    :host([data-tone="danger"]:hover:not(:disabled)) {
      color: #f4dcd8;
      background: rgb(203 105 98 / 16%);
      border-color: rgb(203 105 98 / 48%);
    }
    @media (prefers-reduced-motion: reduce) {
      :host {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminAction {
  readonly tone = input<ActionTone>("quiet");
}
