import { ChangeDetectionStrategy, Component, computed, input } from "@angular/core";
import type { ConnectionState } from "../services/browser-session";

@Component({
  selector: "app-browser-session-header",
  template: `
    <div class="session-identity">
      <span class="session-index">Session {{ paddedPosition() }}</span>
      <strong [title]="label()">{{ label() }}</strong>
    </div>
    <div class="session-tools" aria-label="Session-Metadaten und künftige Werkzeuge">
      <span class="connection-badge" [attr.data-state]="connection()">
        <i aria-hidden="true"></i>{{ connectionLabel() }}
      </span>
      <span class="plane-label">Data Plane</span>
    </div>
  `,
  styles: `
    :host {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      min-height: 43px;
      padding: 7px 13px 7px 15px;
      background: #10141b;
      border-bottom: 1px solid #282f3a;
    }
    .session-identity {
      display: flex;
      align-items: baseline;
      gap: 12px;
      min-width: 0;
    }
    .session-index {
      flex: none;
      color: #7292d8;
      font:
        650 0.66rem/1 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
      letter-spacing: 0.11em;
      text-transform: uppercase;
    }
    strong {
      overflow: hidden;
      color: #aeb8c8;
      font:
        500 0.72rem/1 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .session-tools {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: none;
    }
    .connection-badge,
    .plane-label {
      display: inline-flex;
      align-items: center;
      min-height: 25px;
      padding: 0 9px;
      color: #7f8999;
      font:
        600 0.66rem/1 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
      letter-spacing: 0.04em;
      background: #151a22;
      border: 1px solid #29313e;
      border-radius: 999px;
    }
    .connection-badge {
      gap: 6px;
    }
    .connection-badge i {
      width: 6px;
      height: 6px;
      background: #d5a14e;
      border-radius: 50%;
    }
    .connection-badge[data-state="connected"] {
      color: #a8d9b5;
      border-color: rgb(71 152 92 / 35%);
    }
    .connection-badge[data-state="connected"] i {
      background: #58c879;
      box-shadow: 0 0 0 3px rgb(88 200 121 / 10%);
    }
    .connection-badge[data-state="disconnected"] i {
      background: #e0756b;
    }
    @media (max-width: 580px) {
      :host {
        min-height: 39px;
        padding-inline: 10px;
      }
      .session-identity {
        gap: 8px;
      }
      .session-index {
        font-size: 0.6rem;
      }
      .plane-label {
        display: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserSessionHeader {
  readonly position = input.required<number>();
  readonly label = input.required<string>();
  readonly connection = input.required<ConnectionState>();

  protected readonly paddedPosition = computed(() => this.position().toString().padStart(2, "0"));
  protected readonly connectionLabel = computed(() => {
    switch (this.connection()) {
      case "connected":
        return "Live";
      case "connecting":
        return "Verbindet";
      default:
        return "Offline";
    }
  });
}
