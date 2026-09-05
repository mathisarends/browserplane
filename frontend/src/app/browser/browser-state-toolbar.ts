import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from "@angular/core";
import { BrowserSession } from "./browser-session";
import { BrowserStateVault } from "./browser-state-vault";

type Operation = "capture" | "mount";
type Notice = { readonly tone: "success" | "error"; readonly text: string };

@Component({
  selector: "app-browser-state-toolbar",
  template: `
    <section class="state-toolbar" aria-label="Browserzustand verwalten">
      <div class="state-intro">
        <span class="state-icon" aria-hidden="true">
          <svg viewBox="0 0 20 20">
            <path d="M10 2.8 16 6v8l-6 3.2L4 14V6l6-3.2Z" />
            <path d="m4.4 6.2 5.6 3 5.6-3M10 9.2v7.4" />
          </svg>
        </span>
        <span>
          <strong>Browser State</strong>
          <small>Auth, Tabs &amp; Scroll · temporär in diesem Tab</small>
        </span>
      </div>

      <div class="state-actions">
        <button
          class="capture-button"
          type="button"
          [disabled]="!session.sessionId() || !!operation()"
          (click)="capture()"
        >
          @if (operation() === "capture") {
            <i class="spinner" aria-hidden="true"></i> Speichert …
          } @else {
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="M10 3v9m0 0 3-3m-3 3L7 9" />
              <path d="M4 14v2h12v-2" />
            </svg>
            Zustand sichern
          }
        </button>

        <label class="snapshot-picker">
          <span class="visually-hidden">Gespeicherten Snapshot auswählen</span>
          <select
            [value]="selectedSnapshotId()"
            [disabled]="vault.snapshots().length === 0 || !!operation()"
            (change)="selectedSnapshotId.set($any($event.target).value)"
          >
            <option value="">Snapshot auswählen</option>
            @for (snapshot of vault.snapshots(); track snapshot.id) {
              <option [value]="snapshot.id">
                {{ snapshot.name }} · {{ snapshotTime(snapshot.createdAt) }}
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
          @if (operation() === "mount") {
            <i class="spinner" aria-hidden="true"></i> Mountet …
          } @else {
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="M10 17V8m0 0 3 3m-3-3-3 3" />
              <path d="M4 6V4h12v2" />
            </svg>
            Mounten
          }
        </button>
      </div>

      @if (notice(); as currentNotice) {
        <div class="state-notice" [attr.data-tone]="currentNotice.tone" role="status">
          <i aria-hidden="true"></i>{{ currentNotice.text }}
        </div>
      }
    </section>
  `,
  styles: `
    :host {
      display: block;
    }
    .state-toolbar {
      display: grid;
      grid-template-columns: minmax(190px, auto) minmax(0, 1fr);
      align-items: center;
      gap: 8px 16px;
      padding: 8px 10px;
      background: #121318;
      border-top: 1px solid #292b31;
    }
    .state-intro {
      display: flex;
      align-items: center;
      gap: 9px;
      min-width: 0;
    }
    .state-intro > span:last-child {
      display: grid;
      gap: 2px;
      min-width: 0;
    }
    .state-intro strong {
      color: #e0e2e6;
      font-size: 0.75rem;
      font-weight: 650;
    }
    .state-intro small {
      overflow: hidden;
      color: #747882;
      font-size: 0.65rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .state-icon {
      display: grid;
      place-items: center;
      flex: none;
      width: 30px;
      height: 30px;
      color: #b9bec7;
      background: #1b1d22;
      border: 1px solid #30333a;
      border-radius: 999px;
      box-shadow: inset 0 1px 0 rgb(255 255 255 / 4%);
    }
    .state-icon svg {
      width: 17px;
      height: 17px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.35;
      stroke-linecap: round;
      stroke-linejoin: round;
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
      border-radius: 999px;
    }
    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      padding: 0 11px;
      color: #b9bdc5;
      font-size: 0.7rem;
      font-weight: 650;
      background: #1c1e23;
      border: 1px solid #303238;
      cursor: pointer;
      white-space: nowrap;
    }
    button:hover:not(:disabled) {
      color: #eef3fc;
      background: #292b30;
      border-color: #3a3d44;
    }
    button:focus-visible,
    select:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    button:disabled {
      opacity: 0.45;
      cursor: default;
    }
    button svg {
      width: 15px;
      height: 15px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.55;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .capture-button {
      color: #d6d8dd;
      background: #22242a;
      border-color: #34373e;
    }
    .mount-button:not(:disabled) {
      color: #131417;
      background: #eceef1;
      border-color: #eceef1;
      box-shadow: 0 1px 5px rgb(0 0 0 / 24%);
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
      color: #596474;
    }
    .state-notice {
      grid-column: 2;
      display: flex;
      align-items: center;
      gap: 7px;
      color: #91d4a3;
      font-size: 0.68rem;
    }
    .state-notice i {
      width: 6px;
      height: 6px;
      background: currentcolor;
      border-radius: 50%;
    }
    .state-notice[data-tone="error"] {
      color: #ef8d83;
    }
    .spinner {
      width: 12px;
      height: 12px;
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
    @media (max-width: 760px) {
      .state-toolbar {
        grid-template-columns: minmax(0, 1fr);
      }
      .state-actions {
        grid-template-columns: auto minmax(120px, 1fr) auto;
      }
      .state-notice {
        grid-column: 1;
      }
    }
    @media (max-width: 500px) {
      .state-actions {
        grid-template-columns: 1fr 1fr;
      }
      .snapshot-picker {
        grid-column: 1 / -1;
        grid-row: 1;
      }
      .state-intro small {
        white-space: normal;
        line-height: 1.25;
      }
    }
    @media (prefers-reduced-motion: reduce) {
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
  protected readonly operation = signal<Operation | undefined>(undefined);
  protected readonly selectedSnapshotId = signal("");
  protected readonly notice = signal<Notice | undefined>(undefined);
  protected readonly sourceLabel = computed(
    () => this.session.browserId() ?? `Session ${this.position().toString().padStart(2, "0")}`,
  );

  protected async capture(): Promise<void> {
    const sessionId = this.session.sessionId();
    if (!sessionId) return;
    this.operation.set("capture");
    this.notice.set(undefined);
    try {
      const snapshot = await this.vault.capture(sessionId, this.sourceLabel());
      this.selectedSnapshotId.set(snapshot.id);
      this.notice.set({
        tone: "success",
        text: `${snapshot.name} inklusive Authentication gespeichert`,
      });
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
      this.notice.set({
        tone: "success",
        text: `${snapshot.name} erfolgreich auf diesen Browser gemountet`,
      });
    } catch (error) {
      this.notice.set({ tone: "error", text: errorMessage(error) });
    } finally {
      this.operation.set(undefined);
    }
  }

  protected snapshotTime(date: Date): string {
    return new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(date);
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Browserzustand konnte nicht übertragen werden";
}
