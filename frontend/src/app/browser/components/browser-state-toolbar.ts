import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from "@angular/core";
import { BrowserSession } from "../services/browser-session";
import { BrowserStateVault } from "../services/browser-state-vault";

type Operation = "capture" | "mount";
type Notice = { readonly tone: "success" | "error"; readonly text: string };

@Component({
  selector: "app-browser-state-toolbar",
  template: `
    <div class="state-bar" aria-label="Browser state">
      <button
        class="state-trigger"
        type="button"
        [attr.aria-expanded]="expanded()"
        (click)="toggle()"
      >
        <i class="state-dot" [attr.data-state]="session.connection()" aria-hidden="true"></i>
        <span>State · {{ selectedSnapshot()?.name ?? "Default" }}</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" [class.open]="expanded()">
          <path d="m5 6 3 3 3-3" />
        </svg>
      </button>

      <span class="bar-status" [attr.data-tone]="notice()?.tone">
        @if (operation()) {
          <i class="spinner" aria-hidden="true"></i
          >{{ operation() === "capture" ? "Saving" : "Mounting" }}
        } @else if (notice(); as currentNotice) {
          {{ currentNotice.text }}
        } @else {
          {{ vault.snapshots().length }} saved
        }
      </span>
    </div>

    @if (expanded()) {
      <section class="state-popover" aria-label="Manage browser state">
        <header>
          <span>
            <strong>Browser State</strong>
            <small>Authentication, tabs, and scroll position · saved for this browser</small>
          </span>
          <button
            class="close-button"
            type="button"
            aria-label="Close browser state menu"
            (click)="expanded.set(false)"
          >
            ×
          </button>
        </header>

        <div class="state-actions">
          <button
            class="capture-button"
            type="button"
            [disabled]="!session.sessionId() || !!operation()"
            (click)="capture()"
          >
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="M10 3v9m0 0 3-3m-3 3L7 9" />
              <path d="M4 14v2h12v-2" />
            </svg>
            Save state
          </button>

          <label class="snapshot-picker">
            <span class="visually-hidden">Select saved snapshot</span>
            <select
              [value]="selectedSnapshotId()"
              [disabled]="vault.snapshots().length === 0 || !!operation()"
              (change)="selectedSnapshotId.set($any($event.target).value)"
            >
              <option value="">Select snapshot</option>
              @for (snapshot of vault.snapshots(); track snapshot.id) {
                <option [value]="snapshot.id">
                  {{ snapshot.name }} · {{ snapshotTime(snapshot.created_at) }}
                </option>
              }
            </select>
          </label>

          <button
            class="mount-button"
            type="button"
            [disabled]="!session.sessionId() || !selectedSnapshotId() || !!operation()"
            (click)="mount()"
          >
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="M10 17V8m0 0 3 3m-3-3-3 3" />
              <path d="M4 6V4h12v2" />
            </svg>
            Mount
          </button>
        </div>

        @if (notice(); as currentNotice) {
          <div class="popover-notice" [attr.data-tone]="currentNotice.tone" role="status">
            <i aria-hidden="true"></i>{{ currentNotice.text }}
          </div>
        }
      </section>
    }
  `,
  styles: `
    :host {
      position: relative;
      z-index: 12;
      display: block;
    }
    .state-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      height: 30px;
      padding: 0 8px;
      color: #747982;
      font-size: 0.68rem;
      background: #101116;
      border-top: 1px solid #25272d;
    }
    .state-trigger {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      height: 24px;
      padding: 0 5px;
      color: #9297a0;
      font-size: inherit;
      background: transparent;
      border: 0;
      border-radius: 5px;
      cursor: pointer;
    }
    .state-trigger:hover {
      color: #d7d9de;
      background: #1b1d22;
    }
    .state-trigger:focus-visible,
    button:focus-visible,
    select:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    .state-trigger span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .state-trigger svg {
      flex: none;
      width: 13px;
      height: 13px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.5;
      transition: transform 180ms ease;
    }
    .state-trigger svg.open {
      transform: rotate(180deg);
    }
    .state-dot {
      flex: none;
      width: 6px;
      height: 6px;
      background: #c69a4b;
      border-radius: 50%;
    }
    .state-dot[data-state="connected"] {
      background: #65b879;
    }
    .state-dot[data-state="disconnected"] {
      background: #cb6962;
    }
    .bar-status {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      overflow: hidden;
      color: #60656e;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bar-status[data-tone="success"] {
      color: #73a981;
    }
    .bar-status[data-tone="error"] {
      color: #c9756e;
    }
    .state-popover {
      position: absolute;
      right: 8px;
      bottom: calc(100% + 6px);
      left: 8px;
      display: grid;
      gap: 12px;
      padding: 12px;
      background: rgb(20 21 25 / 97%);
      border: 1px solid #303238;
      border-radius: 12px;
      box-shadow: 0 18px 50px rgb(0 0 0 / 48%);
      backdrop-filter: blur(18px);
      animation: popover-in 180ms cubic-bezier(0.22, 1, 0.36, 1);
    }
    .state-popover header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
    }
    .state-popover header > span {
      display: grid;
      gap: 3px;
    }
    .state-popover strong {
      color: #e3e5e8;
      font-size: 0.78rem;
      font-weight: 650;
    }
    .state-popover small {
      color: #747982;
      font-size: 0.68rem;
    }
    .close-button {
      display: grid;
      place-items: center;
      flex: none;
      width: 24px;
      height: 24px;
      padding: 0 0 2px;
      color: #8a8f98;
      font-size: 1rem;
      background: transparent;
      border: 0;
      border-radius: 6px;
      cursor: pointer;
    }
    .close-button:hover {
      color: #f1f2f4;
      background: #292b30;
    }
    .state-actions {
      display: grid;
      grid-template-columns: auto minmax(150px, 1fr) auto;
      gap: 7px;
      min-width: 0;
    }
    .state-actions button,
    select {
      min-height: 32px;
      border-radius: 8px;
    }
    .state-actions button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      padding: 0 11px;
      color: #c2c5cb;
      font-size: 0.7rem;
      font-weight: 650;
      background: #22242a;
      border: 1px solid #34373e;
      cursor: pointer;
      white-space: nowrap;
    }
    .state-actions button:hover:not(:disabled) {
      color: #f2f3f5;
      background: #2b2d33;
      border-color: #40434a;
    }
    .state-actions button:disabled {
      opacity: 0.42;
      cursor: default;
    }
    .state-actions button svg {
      width: 15px;
      height: 15px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.55;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .mount-button:not(:disabled) {
      color: #151619;
      background: #eceef1;
      border-color: #eceef1;
    }
    .mount-button:hover:not(:disabled) {
      color: #0d0e10;
      background: #fff;
      border-color: #fff;
    }
    .snapshot-picker {
      min-width: 0;
    }
    select {
      width: 100%;
      padding: 0 30px 0 10px;
      color: #b8bcc4;
      font-size: 0.7rem;
      background: #17191d;
      border: 1px solid #303238;
      outline: none;
    }
    select:disabled {
      color: #585d66;
    }
    .popover-notice {
      display: flex;
      align-items: center;
      gap: 7px;
      color: #79ad86;
      font-size: 0.68rem;
    }
    .popover-notice i {
      width: 6px;
      height: 6px;
      background: currentcolor;
      border-radius: 50%;
    }
    .popover-notice[data-tone="error"] {
      color: #cf776f;
    }
    .spinner {
      width: 10px;
      height: 10px;
      border: 1.5px solid currentcolor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 650ms linear infinite;
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
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    @keyframes popover-in {
      from {
        opacity: 0;
        transform: translateY(5px) scale(0.99);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }
    @media (max-width: 560px) {
      .state-actions {
        grid-template-columns: 1fr 1fr;
      }
      .snapshot-picker {
        grid-column: 1 / -1;
        grid-row: 1;
      }
      .state-popover {
        right: 5px;
        left: 5px;
      }
      .bar-status {
        display: none;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .state-trigger svg {
        transition: none;
      }
      .state-popover {
        animation: none;
      }
      .spinner {
        animation-duration: 1.6s;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserStateToolbar {
  readonly position = input.required<number>();
  protected readonly session = inject(BrowserSession);
  protected readonly vault = inject(BrowserStateVault);
  protected readonly expanded = signal(false);
  protected readonly operation = signal<Operation | undefined>(undefined);
  protected readonly selectedSnapshotId = signal("");
  protected readonly notice = signal<Notice | undefined>(undefined);
  protected readonly selectedSnapshot = computed(() =>
    this.vault.snapshots().find(({ id }) => id === this.selectedSnapshotId()),
  );
  protected readonly sourceLabel = computed(
    () => this.session.browserId() ?? `Session ${this.position().toString().padStart(2, "0")}`,
  );

  protected toggle(): void {
    this.expanded.update((value) => !value);
  }

  protected async capture(): Promise<void> {
    const sessionId = this.session.sessionId();
    if (!sessionId) return;
    this.operation.set("capture");
    this.notice.set(undefined);
    try {
      const snapshot = await this.vault.capture(sessionId, this.sourceLabel());
      this.selectedSnapshotId.set(snapshot.id);
      this.notice.set({ tone: "success", text: `${snapshot.name} saved` });
    } catch (error) {
      this.notice.set({ tone: "error", text: errorMessage(error) });
    } finally {
      this.operation.set(undefined);
    }
  }

  protected async mount(): Promise<void> {
    const sessionId = this.session.sessionId();
    const snapshotId = this.selectedSnapshotId();
    if (!sessionId || !snapshotId) return;
    this.operation.set("mount");
    this.notice.set(undefined);
    try {
      const snapshot = await this.vault.mount(sessionId, snapshotId);
      await this.session.refreshTabs();
      this.notice.set({ tone: "success", text: `${snapshot.name} mounted` });
      this.expanded.set(false);
    } catch (error) {
      this.notice.set({ tone: "error", text: errorMessage(error) });
    } finally {
      this.operation.set(undefined);
    }
  }

  protected snapshotTime(timestamp: string): string {
    return new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit" }).format(
      new Date(timestamp),
    );
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Browser state could not be transferred";
}
