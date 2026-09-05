import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import type { TabResult } from "@browsertunnel/browser-rpc-client";

@Component({
  selector: "app-browser-tab-strip",
  template: `
    <div class="window-controls" aria-hidden="true"><span></span><span></span><span></span></div>
    <div class="tabs">
      <div class="tab-list" role="tablist" aria-label="Browser-Tabs">
        @for (tab of tabs(); track tab.id) {
          <div
            class="browser-tab"
            role="tab"
            [tabIndex]="tab.active ? 0 : -1"
            [attr.aria-selected]="tab.active"
            (click)="activate.emit(tab.id)"
          >
            <i aria-hidden="true"></i><span>{{ tab.title || "Neuer Tab" }}</span>
            <button
              type="button"
              class="close-tab"
              [attr.aria-label]="(tab.title || 'Neuer Tab') + ' schließen'"
              (click)="$event.stopPropagation(); close.emit(tab.id)"
            >
              ×
            </button>
          </div>
        }
      </div>
      <button class="new-tab" type="button" aria-label="Neuen Tab öffnen" (click)="create.emit()">
        +
      </button>
    </div>
  `,
  styles: `
    :host {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      height: 42px;
      padding: 7px 12px 0 14px;
      background: #17191e;
    }
    .window-controls {
      display: flex;
      flex: 0 0 58px;
      align-self: center;
      gap: 7px;
    }
    .window-controls span {
      width: 10px;
      height: 10px;
      background: #454b57;
      border-radius: 50%;
      box-shadow: inset 0 0 0 0.5px rgb(0 0 0 / 28%);
    }
    .window-controls span:first-child {
      background: #ff5f57;
    }
    .window-controls span:nth-child(2) {
      background: #febc2e;
    }
    .window-controls span:last-child {
      background: #28c840;
    }
    .tabs {
      display: flex;
      overflow: hidden;
      align-items: center;
      flex: 1;
      min-width: 0;
      height: 34px;
    }
    .tab-list {
      display: flex;
      overflow-x: auto;
      flex: 0 1 auto;
      min-width: 0;
      gap: 3px;
      scrollbar-width: none;
    }
    .browser-tab {
      display: grid;
      grid-template-columns: 9px minmax(0, 1fr) 22px;
      align-items: center;
      gap: 7px;
      flex: 0 1 230px;
      width: 230px;
      min-width: 120px;
      max-width: 250px;
      height: 34px;
      padding: 0 5px 0 11px;
      color: #8f949d;
      background: transparent;
      border: 1px solid transparent;
      border-bottom: 0;
      border-radius: 9px 9px 0 0;
      cursor: default;
      outline: none;
    }
    .browser-tab[aria-selected="true"] {
      color: #f0f1f3;
      background: #26282d;
      border-color: #30333a;
      box-shadow: inset 0 1px 0 rgb(255 255 255 / 3%);
    }
    .browser-tab:focus-visible {
      box-shadow: inset 0 0 0 1px #79a4ff;
    }
    .browser-tab > i {
      width: 7px;
      height: 7px;
      background: #666c76;
      border-radius: 50%;
    }
    .browser-tab[aria-selected="true"] > i {
      background: #b8bdc6;
    }
    .browser-tab > span {
      overflow: hidden;
      font-size: 0.75rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .close-tab,
    .new-tab {
      display: grid;
      place-items: center;
      color: #81868f;
      background: transparent;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
    }
    .close-tab:hover,
    .new-tab:hover {
      color: #f0f1f3;
      background: #303238;
    }
    .close-tab:focus-visible,
    .new-tab:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    .close-tab {
      width: 22px;
      height: 22px;
      padding: 0 0 2px;
      font-size: 1.06rem;
    }
    .new-tab {
      flex: 0 0 28px;
      width: 28px;
      height: 28px;
      margin: 0 0 2px 5px;
      font-size: 1.12rem;
    }
    @media (max-width: 580px) {
      :host {
        gap: 6px;
        height: 39px;
        padding: 6px 8px 0 10px;
      }
      .window-controls {
        flex-basis: 43px;
        gap: 5px;
      }
      .window-controls span {
        width: 8px;
        height: 8px;
      }
      .browser-tab {
        min-width: 105px;
        height: 32px;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserTabStrip {
  readonly tabs = input.required<readonly TabResult[]>();
  readonly activate = output<string>();
  readonly close = output<string>();
  readonly create = output<void>();
}
