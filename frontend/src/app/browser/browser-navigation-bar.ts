import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  input,
  output,
  viewChild,
} from "@angular/core";
import type { NavigationState } from "./browser-session";

@Component({
  selector: "app-browser-navigation-bar",
  template: `
    <nav class="navigation-controls" aria-label="Seitennavigation">
      <button
        type="button"
        aria-label="Zurück"
        [disabled]="!navigation()?.canGoBack"
        (click)="back.emit()"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m12.5 4.5-5.5 5 5.5 5" /></svg>
      </button>
      <button
        type="button"
        aria-label="Vor"
        [disabled]="!navigation()?.canGoForward"
        (click)="forward.emit()"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7.5 4.5 5.5 5-5.5 5" /></svg>
      </button>
      <button
        type="button"
        [disabled]="!hasActiveTab()"
        (click)="reloadOrStop.emit()"
        [attr.data-loading]="navigation()?.loading ?? false"
        [attr.aria-label]="navigation()?.loading ? 'Laden abbrechen' : 'Neu laden'"
      >
        <svg class="reload-icon" viewBox="0 0 20 20" aria-hidden="true">
          <path d="M15.3 7.1A6 6 0 1 0 16 10" />
          <path d="M15.3 3.8v3.7H12" />
        </svg>
        <svg class="stop-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 6h8v8H6z" /></svg>
      </button>
    </nav>
    <form class="address-form" (submit)="$event.preventDefault(); navigate.emit()">
      <label class="visually-hidden" [for]="ownerId() + '-url'">URL</label>
      <input
        #addressInput
        [id]="ownerId() + '-url'"
        name="url"
        type="text"
        inputmode="url"
        [value]="address()"
        (input)="addressChange.emit($any($event.target).value)"
        placeholder="URL eingeben"
        autocomplete="url"
        spellcheck="false"
      />
    </form>
  `,
  styles: `
    :host {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      align-items: center;
      gap: 9px;
      min-height: 45px;
      padding: 7px 12px;
      border-bottom: 1px solid #292e38;
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
    }
    button:hover:not(:disabled) {
      color: #f0f3f7;
      background: #303640;
    }
    button:disabled {
      color: #505761;
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
    input {
      width: 100%;
      height: 32px;
      padding: 0 14px;
      color: #d6dbe4;
      background: #0c1016;
      border: 1px solid #343c49;
      border-radius: 9px;
      outline: none;
    }
    input::placeholder {
      color: #687384;
    }
    input:focus {
      border-color: #719df7;
      box-shadow: 0 0 0 3px rgb(103 151 255 / 14%);
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
        gap: 5px;
        min-height: 42px;
        padding: 5px 7px;
      }
      button {
        width: 27px;
        height: 30px;
      }
      input {
        padding-inline: 10px;
        font-size: 0.84rem;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserNavigationBar {
  readonly ownerId = input.required<string>();
  readonly address = input.required<string>();
  readonly navigation = input<NavigationState>();
  readonly hasActiveTab = input.required<boolean>();
  readonly addressChange = output<string>();
  readonly navigate = output<void>();
  readonly back = output<void>();
  readonly forward = output<void>();
  readonly reloadOrStop = output<void>();
  private readonly addressInput = viewChild<ElementRef<HTMLInputElement>>("addressInput");

  focusAddress(): void {
    this.addressInput()?.nativeElement.focus();
  }
}
