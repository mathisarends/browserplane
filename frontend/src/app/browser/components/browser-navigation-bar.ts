import {
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  input,
  output,
  viewChild,
} from "@angular/core";
import type { NavigationState } from "../services/browser-session";

@Component({
  selector: "app-browser-navigation-bar",
  template: `
    <nav class="navigation-controls" aria-label="Page navigation">
      <button
        type="button"
        aria-label="Back"
        [disabled]="!navigation()?.canGoBack"
        (click)="back.emit()"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M16.3 10H3.7" />
          <path d="m8.7 15-5-5 5-5" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="Forward"
        [disabled]="!navigation()?.canGoForward"
        (click)="forward.emit()"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M3.7 10h12.6" />
          <path d="m11.3 5 5 5-5 5" />
        </svg>
      </button>
      <button
        type="button"
        [disabled]="!hasActiveTab()"
        (click)="reloadOrStop.emit()"
        [attr.data-loading]="navigation()?.loading ?? false"
        [attr.aria-label]="navigation()?.loading ? 'Stop loading' : 'Reload'"
      >
        <svg class="reload-icon" viewBox="0 0 20 20" aria-hidden="true">
          <path d="M16.5 10a6.5 6.5 0 1 1-2.15-4.83" />
          <path d="M16.5 3.5v4.3h-4.3" />
        </svg>
        <svg class="stop-icon" viewBox="0 0 20 20" aria-hidden="true">
          <path d="m5.5 5.5 9 9M14.5 5.5l-9 9" />
        </svg>
      </button>
    </nav>
    <form class="address-form" (submit)="$event.preventDefault(); navigate.emit()">
      <label class="visually-hidden" [for]="panelId() + '-url'">Search or enter address</label>
      <div class="omnibox">
        @if (looksLikeUrl()) {
          <svg class="omnibox-icon" viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="10" cy="10" r="6.75" />
            <path
              d="M3.25 10h13.5M10 3.25c1.8 1.9 2.7 4.15 2.7 6.75S11.8 14.85 10 16.75c-1.8-1.9-2.7-4.15-2.7-6.75S8.2 5.15 10 3.25Z"
            />
          </svg>
        } @else {
          <svg class="omnibox-icon" viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="8.75" cy="8.75" r="5.25" />
            <path d="m12.75 12.75 3.75 3.75" />
          </svg>
        }
        <input
          #addressInput
          [id]="panelId() + '-url'"
          name="url"
          type="text"
          inputmode="search"
          [value]="address()"
          (input)="addressChange.emit($any($event.target).value)"
          placeholder="Search DuckDuckGo or enter address"
          autocomplete="off"
          spellcheck="false"
        />
      </div>
    </form>
  `,
  styles: `
    :host {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      align-items: center;
      gap: 10px;
      min-height: 46px;
      padding: 7px 12px 8px;
      border-bottom: 1px solid #262c36;
      box-shadow: 0 1px 0 rgb(255 255 255 / 3%);
    }
    .navigation-controls {
      display: flex;
      align-items: center;
      gap: 2px;
    }
    button {
      display: grid;
      place-items: center;
      width: 30px;
      height: 30px;
      padding: 0;
      color: #aeb7c4;
      background: transparent;
      border: 0;
      border-radius: 50%;
      cursor: pointer;
      transition:
        color 140ms ease,
        background-color 140ms ease;
    }
    button:hover:not(:disabled) {
      color: #f0f3f7;
      background: #2c323d;
    }
    button:active:not(:disabled) {
      background: #353c48;
    }
    button:disabled {
      color: #4b525d;
      cursor: default;
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    svg {
      width: 18px;
      height: 18px;
      fill: none;
      stroke: currentcolor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
    }
    .stop-icon,
    button[data-loading="true"] .reload-icon {
      display: none;
    }
    button[data-loading="true"] .stop-icon {
      display: inline;
    }
    .address-form {
      min-width: 0;
    }
    .omnibox {
      display: grid;
      grid-template-columns: 16px minmax(0, 1fr);
      align-items: center;
      gap: 9px;
      height: 32px;
      padding: 0 14px;
      background: #10151c;
      border: 1px solid #2c333f;
      border-radius: 999px;
      box-shadow: inset 0 1px 2px rgb(0 0 0 / 28%);
      transition:
        background-color 140ms ease,
        border-color 140ms ease,
        box-shadow 140ms ease;
    }
    .omnibox:hover:not(:focus-within) {
      background: #141a23;
      border-color: #3a4351;
    }
    .omnibox:focus-within {
      background: #1a212c;
      border-color: #48566d;
      box-shadow: 0 1px 4px rgb(0 0 0 / 30%);
    }
    .omnibox-icon {
      width: 16px;
      height: 16px;
      color: #5d6879;
      stroke-width: 1.5;
      transition: color 140ms ease;
    }
    .omnibox:focus-within .omnibox-icon {
      color: #a3aebf;
    }
    input {
      width: 100%;
      min-width: 0;
      height: 100%;
      padding: 0;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      letter-spacing: -0.01em;
      color: #dee4ed;
      text-overflow: ellipsis;
      background: transparent;
      border: 0;
      outline: none;
      caret-color: #79a4ff;
    }
    input::placeholder {
      color: rgb(105 116 134 / 88%);
      font-family: var(--font-sans);
      font-size: 0.8rem;
      letter-spacing: -0.005em;
    }
    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
    @media (max-width: 580px) {
      :host {
        gap: 6px;
        min-height: 42px;
        padding: 5px 7px 6px;
      }
      button {
        width: 27px;
        height: 30px;
      }
      .omnibox {
        grid-template-columns: 14px minmax(0, 1fr);
        gap: 7px;
        padding-inline: 10px;
      }
      .omnibox-icon {
        width: 14px;
        height: 14px;
      }
      input {
        font-size: 0.72rem;
      }
      input::placeholder {
        font-size: 0.76rem;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserNavigationBar {
  readonly panelId = input.required<string>();
  readonly address = input.required<string>();
  readonly navigation = input<NavigationState>();
  readonly hasActiveTab = input.required<boolean>();
  readonly addressChange = output<string>();
  readonly navigate = output<void>();
  readonly back = output<void>();
  readonly forward = output<void>();
  readonly reloadOrStop = output<void>();
  protected readonly looksLikeUrl = computed(() => {
    const value = this.address().trim();
    return /^[a-z][\w+.-]*:\/\//i.test(value) || /^[^\s/]+\.[^\s/]{2,}/.test(value);
  });
  private readonly addressInput = viewChild<ElementRef<HTMLInputElement>>("addressInput");

  focusAddress(): void {
    this.addressInput()?.nativeElement.focus();
  }
}
