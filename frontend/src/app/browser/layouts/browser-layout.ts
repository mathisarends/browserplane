import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from "@angular/core";
import { listOwnerSessions, type SessionResponse } from "@browsertunnel/backend-client";
import { BrowserCreateTile } from "../components/browser-create-tile";
import { BrowserPanel } from "../components/browser-panel";
import { ClientIdentity } from "../services/client-identity";

/** One tile in the gallery: a session taken over, or a browser about to be leased. */
interface GalleryPanel {
  /** Stable across a restore, so Angular keeps the panel it already built. */
  readonly key: string;
  /** Set when the panel picks a session this client already owns back up. */
  readonly sessionId?: string;
}

@Component({
  selector: "app-browser-layout",
  imports: [BrowserCreateTile, BrowserPanel],
  template: `
    <main class="browser-stage" aria-label="Remote Browser Sessions">
      @if (restoreFailed()) {
        <p class="restore-notice" role="status">
          Sessions already running could not be loaded. Reload the page to try again.
        </p>
      }
      <div class="browser-grid">
        @for (panel of panels(); track panel.key; let index = $index) {
          <app-browser-panel
            [panelId]="panel.key"
            [sessionId]="panel.sessionId"
            [position]="index + 1"
            (capacityChange)="handleCapacityChange($event)"
            (sessionLost)="handleSessionLost($event)"
          />
        }
        @if (canCreate()) {
          <app-browser-create-tile (create)="createBrowser()" />
        }
      </div>
    </main>
  `,
  styles: `
    :host {
      display: block;
    }
    .browser-stage {
      width: min(100%, 2560px);
      min-width: 0;
      margin-inline: auto;
    }
    .browser-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: clamp(14px, 1.5vw, 22px);
      min-width: 0;
      animation: grid-enter 380ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    .restore-notice {
      margin: 0 0 12px;
      padding: 9px 14px;
      color: #f0c9c9;
      font-size: 0.82rem;
      background: rgb(58 26 26 / 62%);
      border: 1px solid #6b3232;
      border-radius: 10px;
    }
    .browser-grid app-browser-panel,
    .browser-grid app-browser-create-tile {
      min-width: 0;
    }
    @keyframes grid-enter {
      from {
        opacity: 0;
        transform: scale(0.985);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }
    @media (max-width: 580px) {
      .browser-grid {
        grid-template-columns: minmax(0, 1fr);
        gap: 14px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .browser-grid {
        animation: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserLayout implements OnInit {
  private readonly identity = inject(ClientIdentity);
  protected readonly panels = signal<readonly GalleryPanel[]>([]);
  protected readonly restoreFailed = signal(false);
  private readonly restoring = signal(true);
  private readonly creating = signal(false);
  protected readonly canCreate = computed(() => !this.restoring() && !this.creating());

  ngOnInit(): void {
    void this.restore();
  }

  protected createBrowser(): void {
    if (!this.canCreate()) return;
    this.creating.set(true);
    this.panels.update((panels) => [...panels, { key: crypto.randomUUID() }]);
  }

  protected handleCapacityChange(_remainingCapacity: number): void {
    this.creating.set(false);
  }

  protected handleSessionLost(key: string): void {
    this.panels.update((panels) => panels.filter((panel) => panel.key !== key));
    this.creating.set(false);
  }

  /**
   * Rebuild the gallery from the sessions this client still owns.
   *
   * A lease outlives the page that opened it, so what is running is the
   * backend's answer, not something the frontend could remember: reloading
   * shows the browsers again instead of pretending there are none.
   */
  private async restore(): Promise<void> {
    try {
      const response = await listOwnerSessions({ owner_id: this.identity.ownerId });
      if (response.status !== 200) throw new Error(`Status ${response.status}`);
      this.panels.set(
        [...response.data.sessions].sort(byAge).map((session) => ({
          key: session.id,
          sessionId: session.id,
        })),
      );
    } catch {
      // Nothing was taken over, so the gallery stays empty — but silently
      // empty is exactly what looks like "no browsers are running".
      this.restoreFailed.set(true);
    } finally {
      this.restoring.set(false);
    }
  }
}

/** Oldest first, so a panel keeps its place in the gallery across reloads. */
function byAge(left: SessionResponse, right: SessionResponse): number {
  return left.created_at.localeCompare(right.created_at);
}
