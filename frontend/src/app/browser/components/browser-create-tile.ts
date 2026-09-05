import { ChangeDetectionStrategy, Component, output } from "@angular/core";

@Component({
  selector: "app-browser-create-tile",
  template: `
    <section aria-label="Create a new browser">
      <button type="button" (click)="create.emit()">
        <span class="create-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
        </span>
        <span class="create-copy">
          <strong>Create a new browser</strong>
          <small>Add another browser session</small>
        </span>
      </button>
    </section>
  `,
  styles: `
    :host {
      display: grid;
      min-width: 0;
      aspect-ratio: 4 / 3;
    }
    section {
      display: grid;
      overflow: hidden;
      background: rgb(13 15 19 / 68%);
      border: 1px dashed #2c3037;
      border-radius: 14px;
    }
    button {
      display: grid;
      place-content: center;
      justify-items: center;
      gap: 12px;
      width: 100%;
      padding: 20px;
      color: #aeb3bd;
      background: transparent;
      border: 0;
      cursor: pointer;
      transition:
        color 180ms ease,
        background 180ms ease;
    }
    button:hover {
      color: #f0f1f3;
      background: rgb(255 255 255 / 2.5%);
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 2px;
    }
    .create-icon {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      color: #c5c8cf;
      background: #1b1d22;
      border: 1px solid #32353c;
      border-radius: 999px;
      box-shadow: inset 0 1px 0 rgb(255 255 255 / 4%);
    }
    .create-icon svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.6;
      stroke-linecap: round;
    }
    .create-copy {
      display: grid;
      gap: 4px;
      text-align: center;
    }
    .create-copy strong {
      color: inherit;
      font-size: 0.82rem;
      font-weight: 650;
    }
    .create-copy small {
      color: #686e79;
      font-size: 0.68rem;
    }
    @media (prefers-reduced-motion: reduce) {
      button {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserCreateTile {
  readonly create = output<void>();
}
