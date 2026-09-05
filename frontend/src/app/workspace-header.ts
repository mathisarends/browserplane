import { ChangeDetectionStrategy, Component, input } from "@angular/core";

@Component({
  selector: "app-workspace-header",
  template: `
    <header class="workspace-header">
      <div class="product-mark" aria-hidden="true"><span></span><span></span></div>
      <div class="workspace-title">
        <span class="eyebrow">API Showcase</span>
        <h1>Browser Provisioner</h1>
      </div>
      <div class="workspace-summary" aria-label="Workspace-Status">
        <span class="summary-value">{{ sessionCount() }}</span>
        <span class="summary-label">Remote Browser</span>
      </div>
      <div class="toolbar-reserve" aria-label="Bereich für Browser-Werkzeuge">
        <span class="toolbar-copy">
          <strong>Profiles &amp; State</strong>
          <small>Toolbar vorbereitet</small>
        </span>
        <span class="toolbar-slots" aria-hidden="true"><i></i><i></i><i></i></span>
      </div>
    </header>
  `,
  styles: `
    :host {
      display: block;
    }
    .workspace-header {
      position: sticky;
      z-index: 20;
      top: 0;
      display: grid;
      grid-template-columns: auto minmax(170px, 1fr) auto minmax(280px, 0.7fr);
      align-items: center;
      gap: 16px;
      min-height: 72px;
      padding: 12px 14px;
      background: rgb(13 17 24 / 88%);
      border: 1px solid #222936;
      border-radius: 14px;
      box-shadow: 0 18px 60px rgb(0 0 0 / 24%);
      backdrop-filter: blur(18px);
    }
    .product-mark {
      position: relative;
      width: 36px;
      height: 36px;
      background: linear-gradient(145deg, #79a7ff, #456bd1);
      border: 1px solid rgb(255 255 255 / 18%);
      border-radius: 10px;
      box-shadow: 0 8px 24px rgb(71 111 216 / 25%);
    }
    .product-mark span {
      position: absolute;
      width: 14px;
      height: 10px;
      border: 2px solid #f8fbff;
      border-radius: 3px;
    }
    .product-mark span:first-child {
      top: 8px;
      left: 7px;
    }
    .product-mark span:last-child {
      right: 7px;
      bottom: 7px;
    }
    .workspace-title {
      min-width: 0;
    }
    .eyebrow {
      display: block;
      margin-bottom: 3px;
      color: #71809a;
      font:
        600 0.68rem/1 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
      letter-spacing: 0.13em;
      text-transform: uppercase;
    }
    h1 {
      overflow: hidden;
      margin: 0;
      font-size: clamp(1rem, 1.8vw, 1.2rem);
      font-weight: 650;
      letter-spacing: -0.02em;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .workspace-summary {
      display: flex;
      align-items: center;
      gap: 9px;
      padding-inline: 16px;
      border-inline: 1px solid #252c38;
    }
    .summary-value {
      color: #8db1ff;
      font:
        650 1.15rem/1 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
    }
    .summary-label {
      color: #929dad;
      font-size: 0.78rem;
      white-space: nowrap;
    }
    .toolbar-reserve {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-width: 0;
      padding: 8px 10px 8px 14px;
      background: #10151d;
      border: 1px dashed #303949;
      border-radius: 10px;
    }
    .toolbar-copy {
      display: grid;
      gap: 2px;
      min-width: 0;
    }
    .toolbar-copy strong {
      overflow: hidden;
      color: #b7c0ce;
      font-size: 0.75rem;
      font-weight: 600;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .toolbar-copy small {
      color: #657084;
      font-size: 0.68rem;
      white-space: nowrap;
    }
    .toolbar-slots {
      display: flex;
      gap: 5px;
    }
    .toolbar-slots i {
      display: block;
      width: 26px;
      height: 26px;
      background: #181e28;
      border: 1px solid #293241;
      border-radius: 7px;
    }
    @media (max-width: 820px) {
      .workspace-header {
        grid-template-columns: auto minmax(0, 1fr) auto;
      }
      .toolbar-reserve {
        grid-column: 1 / -1;
      }
    }
    @media (max-width: 580px) {
      .workspace-header {
        position: static;
        gap: 10px;
        min-height: 0;
        padding: 10px;
        border-radius: 11px;
      }
      .product-mark {
        width: 32px;
        height: 32px;
      }
      .workspace-summary {
        padding-left: 10px;
        padding-right: 0;
        border-right: 0;
      }
      .summary-label,
      .toolbar-copy small {
        display: none;
      }
      .toolbar-reserve {
        min-height: 42px;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceHeader {
  readonly sessionCount = input.required<number>();
}
