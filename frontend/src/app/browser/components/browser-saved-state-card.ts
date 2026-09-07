import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

export type SavedStateKind = "browser" | "authentication";

export interface SavedStateOption {
  readonly id: string;
  readonly label: string;
}

export interface SavedStateCardView {
  readonly kind: SavedStateKind;
  readonly badge: string;
  readonly title: string;
  readonly subtitle: string;
  readonly pickerLabel: string;
  readonly placeholder: string;
  readonly options: readonly SavedStateOption[];
  readonly selectedId: string;
}

@Component({
  selector: "app-browser-saved-state-card",
  template: `
    <article [attr.data-kind]="card().kind">
      <div class="card-heading">
        <span class="state-icon" aria-hidden="true">{{ card().badge }}</span>
        <span>
          <strong>{{ card().title }}</strong>
          <small>{{ card().subtitle }}</small>
        </span>
        <span class="state-count">{{ card().options.length }}</span>
      </div>

      <div class="state-actions">
        <button type="button" [disabled]="!connected() || busy()" (click)="capture.emit()">
          Save
        </button>

        <label class="saved-state-picker">
          <span class="visually-hidden">{{ card().pickerLabel }}</span>
          <select
            [value]="selectedId()"
            [attr.data-empty]="!selectedId()"
            [disabled]="!card().options.length || busy()"
            (change)="selectedIdChange.emit($any($event.target).value)"
          >
            <option value="">
              {{ card().options.length ? card().placeholder : "None saved" }}
            </option>
            @for (option of card().options; track option.id) {
              <option [value]="option.id">{{ option.label }}</option>
            }
          </select>
          <svg class="picker-chevron" viewBox="0 0 16 16" aria-hidden="true">
            <path d="m5 6.5 3 3 3-3" />
          </svg>
        </label>

        <button
          class="mount-button"
          type="button"
          [disabled]="!connected() || !selectedId() || busy()"
          (click)="mount.emit()"
        >
          Mount
        </button>
      </div>
    </article>
  `,
  styles: `
    :host {
      display: block;
    }
    article {
      display: grid;
      gap: 10px;
      padding: 10px;
      background: #191b20;
      border: 1px solid #2e3037;
      border-left: 2px solid #668de0;
      border-radius: 10px;
    }
    article[data-kind="authentication"] {
      border-left-color: #b184d6;
    }
    .card-heading {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      gap: 9px;
      align-items: center;
    }
    .card-heading > span:nth-child(2) {
      display: grid;
      gap: 2px;
    }
    strong {
      color: #e7e9ec;
      font-size: 0.79rem;
      font-weight: 650;
      letter-spacing: -0.01em;
    }
    small {
      color: #6f747d;
      font-size: 0.62rem;
    }
    .state-icon {
      display: grid;
      place-items: center;
      width: 25px;
      height: 25px;
      color: #a9c2f5;
      font-family: var(--font-mono);
      font-size: 0.65rem;
      font-weight: 700;
      background: #202b42;
      border-radius: 7px;
    }
    article[data-kind="authentication"] .state-icon {
      color: #d2afea;
      background: #30243a;
    }
    .state-count {
      min-width: 22px;
      padding: 3px 6px;
      color: #858a93;
      font-family: var(--font-mono);
      font-size: 0.61rem;
      text-align: center;
      background: #22242a;
      border-radius: 999px;
    }
    .state-actions {
      display: grid;
      grid-template-columns: auto minmax(150px, 1fr) auto;
      gap: 7px;
      min-width: 0;
    }
    button,
    select {
      min-height: 32px;
      border-radius: 8px;
    }
    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 11px;
      color: #c2c5cb;
      font-size: 0.7rem;
      font-weight: 650;
      background: #22242a;
      border: 1px solid #34373e;
      box-shadow: inset 0 1px 0 rgb(255 255 255 / 4%);
      cursor: pointer;
      white-space: nowrap;
      transition:
        color 130ms ease,
        background-color 130ms ease,
        border-color 130ms ease;
    }
    button:hover:not(:disabled) {
      color: #f2f3f5;
      background: #2b2d33;
      border-color: #43464e;
    }
    button:active:not(:disabled) {
      background: #303239;
    }
    button:disabled {
      color: #666b74;
      background: #1c1e23;
      border-color: #2b2d33;
      box-shadow: none;
      cursor: default;
    }
    .mount-button:not(:disabled) {
      color: #151619;
      background: #eceef1;
      border-color: #eceef1;
      box-shadow: inset 0 -1px 0 rgb(0 0 0 / 8%);
    }
    .mount-button:hover:not(:disabled) {
      color: #0d0e10;
      background: #fff;
      border-color: #fff;
    }
    .mount-button:active:not(:disabled) {
      background: #dfe2e6;
      border-color: #dfe2e6;
    }
    button:focus-visible,
    select:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    .saved-state-picker {
      position: relative;
      display: grid;
      min-width: 0;
    }
    select {
      width: 100%;
      padding: 0 30px 0 11px;
      color: #c2c6cd;
      font-size: 0.7rem;
      background: #16181d;
      border: 1px solid #2e3037;
      box-shadow: inset 0 1px 2px rgb(0 0 0 / 26%);
      outline: none;
      appearance: none;
      cursor: pointer;
      text-overflow: ellipsis;
      transition:
        background-color 130ms ease,
        border-color 130ms ease;
    }
    select:hover:not(:disabled) {
      background: #1a1c22;
      border-color: #3b3e46;
    }
    select:focus {
      border-color: #474b55;
    }
    select[data-empty="true"] {
      color: #71767f;
    }
    select:disabled {
      color: #585d66;
      background: #191b1f;
      border-color: #2a2c32;
      box-shadow: none;
      cursor: default;
    }
    select option {
      color: #d6d9df;
      background: #1c1e23;
    }
    .picker-chevron {
      position: absolute;
      top: 50%;
      right: 10px;
      width: 13px;
      height: 13px;
      margin-top: -6.5px;
      color: #71767f;
      fill: none;
      stroke: currentcolor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.5;
      pointer-events: none;
    }
    select:disabled ~ .picker-chevron {
      color: #4d525a;
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
    @media (max-width: 560px) {
      .state-actions {
        grid-template-columns: 1fr 1fr;
      }
      .saved-state-picker {
        grid-column: 1 / -1;
        grid-row: 1;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserSavedStateCard {
  readonly card = input.required<SavedStateCardView>();
  readonly selectedId = input.required<string>();
  readonly connected = input.required<boolean>();
  readonly busy = input.required<boolean>();

  readonly capture = output<void>();
  readonly mount = output<void>();
  readonly selectedIdChange = output<string>();
}
