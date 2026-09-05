import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { AdminConsole } from "../services/admin-console";

/** The outcome of the last action, until it is dismissed or replaced. */
@Component({
  selector: "app-admin-notice",
  template: `
    @if (console.notice(); as notice) {
      <p [attr.data-tone]="notice.tone" role="status">
        <i aria-hidden="true"></i>
        <span>{{ notice.text }}</span>
        <button type="button" aria-label="Dismiss" (click)="console.dismissNotice()">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="m4.5 4.5 7 7M11.5 4.5l-7 7" />
          </svg>
        </button>
      </p>
    }
  `,
  styles: `
    :host {
      display: block;
    }
    :host:empty {
      display: none;
    }
    p {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 7px 8px 7px 12px;
      margin: 0;
      color: var(--admin-free);
      font-size: 0.72rem;
      background: rgb(88 168 110 / 8%);
      border: 1px solid rgb(88 168 110 / 22%);
      border-radius: 10px;
    }
    p[data-tone="error"] {
      color: var(--admin-bad);
      background: rgb(203 105 98 / 8%);
      border-color: rgb(203 105 98 / 26%);
    }
    i {
      flex: none;
      width: 5px;
      height: 5px;
      background: currentcolor;
      border-radius: 50%;
    }
    span {
      flex: 1;
      min-width: 0;
    }
    button {
      display: grid;
      place-items: center;
      flex: none;
      width: 22px;
      height: 22px;
      padding: 0;
      color: inherit;
      background: transparent;
      border: 0;
      border-radius: 6px;
      cursor: pointer;
    }
    button:hover {
      background: rgb(255 255 255 / 7%);
    }
    button:focus-visible {
      outline: 2px solid var(--admin-focus);
      outline-offset: 1px;
    }
    svg {
      width: 11px;
      height: 11px;
      fill: none;
      stroke: currentcolor;
      stroke-linecap: round;
      stroke-width: 1.6;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminNotice {
  protected readonly console = inject(AdminConsole);
}
