import { ChangeDetectionStrategy, Component, input } from "@angular/core";

/** Colour tiers, not one colour per state: green is free, amber is in use. */
type Tone = "free" | "busy" | "idle" | "bad";

const TONES: Record<string, Tone> = {
  ready: "free",
  active: "free",
  leased: "busy",
  starting: "busy",
  stopping: "busy",
  suspended: "idle",
  stopped: "idle",
  failed: "bad",
};

@Component({
  selector: "app-admin-status-pill",
  template: `
    <span [attr.data-tone]="tone()">
      <i aria-hidden="true"></i>
      {{ status() }}
    </span>
  `,
  styles: `
    :host {
      display: inline-flex;
    }
    span {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      height: 21px;
      padding: 0 9px 0 7px;
      color: #9aa0aa;
      font-family: var(--font-mono);
      font-size: 0.63rem;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      background: #1a1c22;
      border: 1px solid #2c2f36;
      border-radius: 999px;
      white-space: nowrap;
    }
    i {
      width: 6px;
      height: 6px;
      background: currentcolor;
      border-radius: 50%;
    }
    span[data-tone="free"] {
      color: #77bb8a;
      background: rgb(88 168 110 / 10%);
      border-color: rgb(88 168 110 / 26%);
    }
    span[data-tone="busy"] {
      color: #d3a95f;
      background: rgb(198 154 75 / 10%);
      border-color: rgb(198 154 75 / 26%);
    }
    span[data-tone="idle"] {
      color: #8b93a0;
    }
    span[data-tone="bad"] {
      color: #d1786f;
      background: rgb(203 105 98 / 10%);
      border-color: rgb(203 105 98 / 28%);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminStatusPill {
  readonly status = input.required<string>();

  protected tone(): Tone {
    return TONES[this.status()] ?? "idle";
  }
}
