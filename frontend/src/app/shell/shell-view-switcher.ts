import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { APP_VIEWS, type AppView } from "./view-mode";

const LABELS: Record<AppView, string> = {
  grid: "Grid",
  focus: "Focus",
  admin: "Admin",
};

@Component({
  selector: "app-shell-view-switcher",
  template: `
    <header>
      <div role="group" aria-label="Workspace view">
        @for (option of views; track option) {
          <button
            type="button"
            [attr.aria-pressed]="view() === option"
            (click)="viewChange.emit(option)"
          >
            {{ label(option) }}
          </button>
        }
      </div>
    </header>
  `,
  styles: `
    :host {
      display: block;
    }
    header {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-bottom: clamp(14px, 1.6vw, 26px);
    }
    div {
      display: inline-flex;
      width: 306px;
      padding: 2px;
      background: #191a1d;
      border: 1px solid #2b2d31;
      border-radius: 999px;
      box-shadow:
        inset 0 1px 0 rgb(255 255 255 / 3%),
        0 8px 24px rgb(0 0 0 / 18%);
    }
    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 1;
      min-height: 31px;
      padding: 0 16px;
      color: #a8acb4;
      font-size: 0.8rem;
      font-weight: 600;
      background: transparent;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      transition:
        color 180ms ease,
        background 180ms ease,
        box-shadow 180ms ease;
    }
    button[aria-pressed="true"] {
      color: #f4f5f7;
      background: #282a2e;
      box-shadow:
        inset 0 1px 0 rgb(255 255 255 / 4%),
        0 1px 4px rgb(0 0 0 / 28%);
    }
    button:hover:not([aria-pressed="true"]) {
      color: #d7d9de;
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 2px;
    }
    @media (max-width: 580px) {
      header {
        margin-bottom: 12px;
      }
      div {
        width: 100%;
        max-width: 306px;
      }
      button {
        padding: 0 10px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      button {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellViewSwitcher {
  readonly view = input.required<AppView>();
  readonly viewChange = output<AppView>();
  protected readonly views = APP_VIEWS;

  protected label(view: AppView): string {
    return LABELS[view];
  }
}
