import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from "@angular/core";
import { BrowserSession } from "../services/browser-session";
import { BrowserPersistenceVault } from "../services/browser-persistence-vault";

type StateKind = "browser" | "authentication";
type Operation = `${StateKind}-${"capture" | "mount"}`;
type Notice = { readonly tone: "success" | "error"; readonly text: string };

@Component({
  selector: "app-browser-state-toolbar",
  template: `
    <div class="state-bar" aria-label="Browser persistence">
      <button
        class="state-trigger"
        type="button"
        [attr.aria-expanded]="expanded()"
        (click)="toggle()"
      >
        <i class="state-dot" [attr.data-state]="session.connection()" aria-hidden="true"></i>
        <span>Checkpoints & profiles</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" [class.open]="expanded()">
          <path d="m5 6 3 3 3-3" />
        </svg>
      </button>

      <span class="bar-status" [attr.data-tone]="notice()?.tone">
        @if (operation()) {
          <i class="spinner" aria-hidden="true"></i
          >{{ operation()?.endsWith("capture") ? "Saving" : "Mounting" }}
        } @else if (notice(); as currentNotice) {
          {{ currentNotice.text }}
        } @else {
          {{ savedCount() }} saved
        }
      </span>
    </div>

    @if (expanded()) {
      <section class="state-popover" aria-label="Manage checkpoints and profiles">
        <header>
          <span>
            <strong>Checkpoints & profiles</strong>
            <small>Restore browser state and reusable login identities.</small>
          </span>
          <button
            class="close-button"
            type="button"
            aria-label="Close browser state menu"
            (click)="expanded.set(false)"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="m4.5 4.5 7 7M11.5 4.5l-7 7" />
            </svg>
          </button>
        </header>

        <div class="state-grid">
          <article class="state-card browser-card">
            <div class="card-heading">
              <span class="state-icon" aria-hidden="true">B</span>
              <span
                ><strong>Browser Checkpoint</strong
                ><small>Tabs, active page, and scroll</small></span
              >
              <span class="state-count">{{ vault.checkpoints().length }}</span>
            </div>
            <div class="state-actions">
              <button
                type="button"
                [disabled]="!session.sessionId() || !!operation()"
                (click)="capture('browser')"
              >
                Save
              </button>
              <label class="saved-state-picker">
                <span class="visually-hidden">Select browser checkpoint</span>
                <select
                  [value]="selectedBrowserId()"
                  [attr.data-empty]="!selectedBrowserId()"
                  [disabled]="!vault.checkpoints().length || !!operation()"
                  (change)="selectedBrowserId.set($any($event.target).value)"
                >
                  <option value="">
                    {{ vault.checkpoints().length ? "Select checkpoint" : "None saved" }}
                  </option>
                  @for (checkpoint of vault.checkpoints(); track checkpoint.id) {
                    <option [value]="checkpoint.id">
                      Checkpoint · {{ savedAt(checkpoint.created_at) }}
                    </option>
                  }
                </select>
                <svg class="picker-chevron" viewBox="0 0 16 16" aria-hidden="true">
                  <path d="m5 6.5 3 3 3-3" />
                </svg>
              </label>
              <button
                class="mount-button"
                type="button"
                [disabled]="!session.sessionId() || !selectedBrowserId() || !!operation()"
                (click)="mount('browser')"
              >
                Mount
              </button>
            </div>
          </article>

          <article class="state-card authentication-card">
            <div class="card-heading">
              <span class="state-icon" aria-hidden="true">A</span>
              <span
                ><strong>Authentication Profile</strong><small>Reusable login identity</small></span
              >
              <span class="state-count">{{ vault.authenticationProfiles().length }}</span>
            </div>
            <div class="state-actions">
              <button
                type="button"
                [disabled]="!session.sessionId() || !!operation()"
                (click)="capture('authentication')"
              >
                Save
              </button>
              <label class="saved-state-picker">
                <span class="visually-hidden">Select authentication profile</span>
                <select
                  [value]="selectedAuthenticationId()"
                  [attr.data-empty]="!selectedAuthenticationId()"
                  [disabled]="!vault.authenticationProfiles().length || !!operation()"
                  (change)="selectedAuthenticationId.set($any($event.target).value)"
                >
                  <option value="">
                    {{ vault.authenticationProfiles().length ? "Select profile" : "None saved" }}
                  </option>
                  @for (profile of vault.authenticationProfiles(); track profile.id) {
                    <option [value]="profile.id">
                      {{ profile.name }} · {{ savedAt(profile.created_at) }}
                    </option>
                  }
                </select>
                <svg class="picker-chevron" viewBox="0 0 16 16" aria-hidden="true">
                  <path d="m5 6.5 3 3 3-3" />
                </svg>
              </label>
              <button
                class="mount-button"
                type="button"
                [disabled]="!session.sessionId() || !selectedAuthenticationId() || !!operation()"
                (click)="mount('authentication')"
              >
                Mount
              </button>
            </div>
          </article>
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
      font-family: var(--font-mono);
      font-size: 0.66rem;
      letter-spacing: 0.01em;
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
      background: rgb(22 23 28 / 97%);
      border: 1px solid #34363d;
      border-radius: 13px;
      box-shadow:
        0 20px 56px rgb(0 0 0 / 52%),
        inset 0 1px 0 rgb(255 255 255 / 4%);
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
      gap: 4px;
      min-width: 0;
    }
    .state-popover strong {
      color: #e7e9ec;
      font-size: 0.79rem;
      font-weight: 650;
      letter-spacing: -0.01em;
    }
    .state-popover small {
      color: #767b85;
      font-size: 0.68rem;
      line-height: 1.45;
    }
    .close-button {
      display: grid;
      place-items: center;
      flex: none;
      width: 24px;
      height: 24px;
      padding: 0;
      margin: -2px -3px 0 0;
      color: #7d828b;
      background: transparent;
      border: 0;
      border-radius: 7px;
      cursor: pointer;
      transition:
        color 130ms ease,
        background-color 130ms ease;
    }
    .close-button svg {
      width: 14px;
      height: 14px;
      fill: none;
      stroke: currentcolor;
      stroke-linecap: round;
      stroke-width: 1.5;
    }
    .close-button:hover {
      color: #f1f2f4;
      background: #2b2d34;
    }
    .state-grid {
      display: grid;
      gap: 9px;
    }
    .state-card {
      display: grid;
      gap: 10px;
      padding: 10px;
      background: #191b20;
      border: 1px solid #2e3037;
      border-radius: 10px;
    }
    .browser-card {
      border-left: 2px solid #668de0;
    }
    .authentication-card {
      border-left: 2px solid #b184d6;
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
    .card-heading small {
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
    .authentication-card .state-icon {
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
      box-shadow: inset 0 1px 0 rgb(255 255 255 / 4%);
      cursor: pointer;
      white-space: nowrap;
      transition:
        color 130ms ease,
        background-color 130ms ease,
        border-color 130ms ease;
    }
    .state-actions button:hover:not(:disabled) {
      color: #f2f3f5;
      background: #2b2d33;
      border-color: #43464e;
    }
    .state-actions button:active:not(:disabled) {
      background: #303239;
    }
    .state-actions button:disabled {
      color: #666b74;
      background: #1c1e23;
      border-color: #2b2d33;
      box-shadow: none;
      cursor: default;
    }
    .state-actions button svg {
      flex: none;
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
      .saved-state-picker {
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
  protected readonly vault = inject(BrowserPersistenceVault);
  protected readonly expanded = signal(false);
  protected readonly operation = signal<Operation | undefined>(undefined);
  protected readonly selectedBrowserId = signal("");
  protected readonly selectedAuthenticationId = signal("");
  protected readonly notice = signal<Notice | undefined>(undefined);
  protected readonly savedCount = computed(
    () => this.vault.checkpoints().length + this.vault.authenticationProfiles().length,
  );
  protected toggle(): void {
    this.expanded.update((value) => !value);
  }

  protected async capture(kind: StateKind): Promise<void> {
    const sessionId = this.session.sessionId();
    if (!sessionId) return;
    this.operation.set(`${kind}-capture`);
    this.notice.set(undefined);
    try {
      const saved =
        kind === "browser"
          ? await this.vault.createCheckpoint(sessionId)
          : await this.vault.createProfile(sessionId);
      if (kind === "browser") this.selectedBrowserId.set(saved.id);
      else this.selectedAuthenticationId.set(saved.id);
      this.notice.set({ tone: "success", text: `${kind} saved` });
    } catch (error) {
      this.notice.set({ tone: "error", text: errorMessage(error) });
    } finally {
      this.operation.set(undefined);
    }
  }

  protected async mount(kind: StateKind): Promise<void> {
    const sessionId = this.session.sessionId();
    const savedStateId =
      kind === "browser" ? this.selectedBrowserId() : this.selectedAuthenticationId();
    if (!sessionId || !savedStateId) return;
    this.operation.set(`${kind}-mount`);
    this.notice.set(undefined);
    try {
      const saved =
        kind === "browser"
          ? await this.vault.mountCheckpoint(sessionId, savedStateId)
          : await this.vault.mountProfile(sessionId, savedStateId);
      if (kind === "browser") await this.session.refreshTabs();
      this.notice.set({
        tone: "success",
        text: `${"name" in saved ? saved.name : "Checkpoint"} mounted`,
      });
    } catch (error) {
      this.notice.set({ tone: "error", text: errorMessage(error) });
    } finally {
      this.operation.set(undefined);
    }
  }

  protected savedAt(timestamp: string): string {
    return new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit" }).format(
      new Date(timestamp),
    );
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Browser state could not be transferred";
}
