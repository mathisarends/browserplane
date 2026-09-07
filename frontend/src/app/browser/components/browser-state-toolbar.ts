import { ChangeDetectionStrategy, Component, computed, inject, signal } from "@angular/core";
import { BrowserSession } from "../services/browser-session";
import { BrowserPersistenceVault } from "../services/browser-persistence-vault";
import {
  BrowserSavedStateCard,
  type SavedStateCardView,
  type SavedStateKind,
} from "./browser-saved-state-card";
import { errorMessage } from "../../shared/errors";

type Notice = { readonly tone: "success" | "error"; readonly text: string };
type Operation = `${SavedStateKind}-${"capture" | "mount"}`;

const KINDS: readonly SavedStateKind[] = ["browser", "authentication"];
const SAVED_AT = new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit" });

@Component({
  selector: "app-browser-state-toolbar",
  imports: [BrowserSavedStateCard],
  template: `
    <div class="state-bar" aria-label="Browser persistence">
      <button
        class="state-trigger"
        type="button"
        [attr.aria-expanded]="expanded()"
        (click)="expanded.set(!expanded())"
      >
        <i class="state-dot" [attr.data-state]="session.connection()" aria-hidden="true"></i>
        <span>Checkpoints &amp; profiles</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" [class.open]="expanded()">
          <path d="m5 6 3 3 3-3" />
        </svg>
      </button>

      <span class="bar-status" [attr.data-tone]="notice()?.tone">
        @if (operation(); as running) {
          <i class="spinner" aria-hidden="true"></i
          >{{ running.endsWith("capture") ? "Saving" : "Mounting" }}
        } @else if (notice(); as current) {
          {{ current.text }}
        } @else {
          {{ savedCount() }} saved
        }
      </span>
    </div>

    @if (expanded()) {
      <section class="state-popover" aria-label="Manage checkpoints and profiles">
        <header>
          <span>
            <strong>Checkpoints &amp; profiles</strong>
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
          @for (card of cards(); track card.kind) {
            <app-browser-saved-state-card
              [card]="card"
              [selectedId]="card.selectedId"
              [connected]="!!session.sessionId()"
              [busy]="!!operation()"
              (selectedIdChange)="select(card.kind, $event)"
              (capture)="capture(card.kind)"
              (mount)="mount(card.kind)"
            />
          }
        </div>

        @if (notice(); as current) {
          <div class="popover-notice" [attr.data-tone]="current.tone" role="status">
            <i aria-hidden="true"></i>{{ current.text }}
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
    .close-button:focus-visible {
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
  protected readonly session = inject(BrowserSession);
  private readonly vault = inject(BrowserPersistenceVault);

  protected readonly expanded = signal(false);
  protected readonly operation = signal<Operation | undefined>(undefined);
  protected readonly notice = signal<Notice | undefined>(undefined);

  private readonly selection = {
    browser: signal(""),
    authentication: signal(""),
  } as const;

  private readonly kinds = {
    browser: {
      badge: "B",
      title: "Browser Checkpoint",
      subtitle: "Tabs, active page, and scroll",
      pickerLabel: "Select browser checkpoint",
      placeholder: "Select checkpoint",
      options: computed(() =>
        this.vault.checkpoints().map((checkpoint) => ({
          id: checkpoint.id,
          label: `Checkpoint · ${savedAt(checkpoint.created_at)}`,
          name: "Checkpoint",
        })),
      ),
      capture: (sessionId: string) => this.vault.createCheckpoint(sessionId),
      mount: async (sessionId: string, id: string) => {
        await this.vault.mountCheckpoint(sessionId, id);
        await this.session.refreshTabs();
      },
    },
    authentication: {
      badge: "A",
      title: "Authentication Profile",
      subtitle: "Reusable login identity",
      pickerLabel: "Select authentication profile",
      placeholder: "Select profile",
      options: computed(() =>
        this.vault.authenticationProfiles().map((profile) => ({
          id: profile.id,
          label: `${profile.name} · ${savedAt(profile.created_at)}`,
          name: profile.name,
        })),
      ),
      capture: (sessionId: string) => this.vault.createProfile(sessionId),
      mount: (sessionId: string, id: string) => this.vault.mountProfile(sessionId, id),
    },
  } as const;

  protected readonly cards = computed<readonly SavedStateCardView[]>(() =>
    KINDS.map((kind) => {
      const { badge, title, subtitle, pickerLabel, placeholder, options } = this.kinds[kind];
      return {
        kind,
        badge,
        title,
        subtitle,
        pickerLabel,
        placeholder,
        options: options(),
        selectedId: this.selection[kind](),
      };
    }),
  );
  protected readonly savedCount = computed(() =>
    KINDS.reduce((total, kind) => total + this.kinds[kind].options().length, 0),
  );

  protected select(kind: SavedStateKind, id: string): void {
    this.selection[kind].set(id);
  }

  protected async capture(kind: SavedStateKind): Promise<void> {
    const sessionId = this.session.sessionId();
    if (!sessionId) return;
    await this.run(`${kind}-capture`, async () => {
      const saved = await this.kinds[kind].capture(sessionId);
      this.selection[kind].set(saved.id);
      return `${kind} saved`;
    });
  }

  protected async mount(kind: SavedStateKind): Promise<void> {
    const sessionId = this.session.sessionId();
    const savedStateId = this.selection[kind]();
    if (!sessionId || !savedStateId) return;
    await this.run(`${kind}-mount`, async () => {
      await this.kinds[kind].mount(sessionId, savedStateId);
      return `${this.nameOf(kind, savedStateId)} mounted`;
    });
  }

  private nameOf(kind: SavedStateKind, id: string): string {
    return this.kinds[kind].options().find((option) => option.id === id)?.name ?? "Saved state";
  }

  private async run(operation: Operation, action: () => Promise<string>): Promise<void> {
    this.operation.set(operation);
    this.notice.set(undefined);
    try {
      this.notice.set({ tone: "success", text: await action() });
    } catch (error) {
      this.notice.set({
        tone: "error",
        text: errorMessage(error, "Browser state could not be transferred"),
      });
    } finally {
      this.operation.set(undefined);
    }
  }
}

function savedAt(timestamp: string): string {
  return SAVED_AT.format(new Date(timestamp));
}
