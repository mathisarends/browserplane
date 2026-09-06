import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
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
      <div class="carousel" [class.is-focused]="focused()">
        @if (focused()) {
          <button
            type="button"
            class="chevron"
            aria-label="Previous browser"
            [disabled]="slideCount() < 2"
            (click)="step(-1)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
          </button>
        }
        <div class="browser-grid" [class.is-focused]="focused()">
          @for (panel of panels(); track panel.key; let index = $index) {
            <app-browser-panel
              [class.is-offstage]="focused() && focusIndex() !== index"
              [panelId]="panel.key"
              [sessionId]="panel.sessionId"
              [position]="index + 1"
              (capacityChange)="handleCapacityChange($event)"
              (sessionLost)="handleSessionLost($event)"
            />
          }
          @if (canCreate()) {
            <app-browser-create-tile
              [class.is-offstage]="focused() && focusIndex() !== panels().length"
              (create)="createBrowser()"
            />
          }
        </div>
        @if (focused()) {
          <button
            type="button"
            class="chevron"
            aria-label="Next browser"
            [disabled]="slideCount() < 2"
            (click)="step(1)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
          </button>
        }
      </div>
      @if (focused() && slideCount() > 0) {
        <p class="focus-counter" role="status" aria-live="polite">
          {{ focusIndex() + 1 }} / {{ slideCount() }}
        </p>
      }
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
    .carousel {
      display: block;
      min-width: 0;
    }
    .carousel.is-focused {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: clamp(8px, 1.2vw, 20px);
    }
    .browser-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: clamp(14px, 1.5vw, 22px);
      min-width: 0;
      animation: grid-enter 380ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    /*
      One slide at a time, and the rest merely offstage: a hidden panel keeps
      its session, its socket and its stream, so stepping through the carousel
      costs nothing.
    */
    .browser-grid.is-focused {
      grid-template-columns: minmax(0, 1fr);
      width: min(100%, 1680px);
    }
    .browser-grid.is-focused > .is-offstage {
      display: none;
    }
    .chevron {
      display: grid;
      place-items: center;
      flex: none;
      width: clamp(38px, 3.2vw, 52px);
      height: clamp(38px, 3.2vw, 52px);
      color: #c5c8cf;
      background: #16181d;
      border: 1px solid #2b2d31;
      border-radius: 999px;
      cursor: pointer;
      transition:
        color 180ms ease,
        background 180ms ease,
        opacity 180ms ease;
    }
    .chevron svg {
      width: 22px;
      height: 22px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.8;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .chevron:hover:not(:disabled) {
      color: #f4f5f7;
      background: #22252a;
    }
    .chevron:disabled {
      opacity: 35%;
      cursor: default;
    }
    .chevron:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 2px;
    }
    .focus-counter {
      margin: clamp(10px, 1.2vw, 18px) 0 0;
      color: #686e79;
      font-size: 0.72rem;
      font-variant-numeric: tabular-nums;
      text-align: center;
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
      .carousel.is-focused {
        gap: 6px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .browser-grid {
        animation: none;
      }
      .chevron {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserLayout implements OnInit {
  /** Show a single slide with chevrons instead of the whole gallery. */
  readonly focused = input(false);
  private readonly identity = inject(ClientIdentity);
  protected readonly panels = signal<readonly GalleryPanel[]>([]);
  protected readonly restoreFailed = signal(false);
  private readonly restoring = signal(true);
  private readonly creating = signal(false);
  protected readonly canCreate = computed(() => !this.restoring() && !this.creating());
  /** The create tile is the last slide, so a new browser stays one step away. */
  protected readonly slideCount = computed(() => this.panels().length + (this.canCreate() ? 1 : 0));
  private readonly requestedIndex = signal(0);
  /**
   * Clamped rather than stored: panels come and go while the carousel is open,
   * and an index left pointing past the end would show an empty stage.
   */
  protected readonly focusIndex = computed(() =>
    Math.min(this.requestedIndex(), Math.max(0, this.slideCount() - 1)),
  );

  ngOnInit(): void {
    void this.restore();
  }

  /** Wraps, so the chevrons never dead-end on the first or last browser. */
  protected step(direction: 1 | -1): void {
    const count = this.slideCount();
    if (count < 2) return;
    this.requestedIndex.set((this.focusIndex() + direction + count) % count);
  }

  protected createBrowser(): void {
    if (!this.canCreate()) return;
    this.creating.set(true);
    this.panels.update((panels) => [...panels, { key: crypto.randomUUID() }]);
    // Follow the browser that was just asked for, instead of staying on a
    // create tile that has left the carousel.
    if (this.focused()) this.requestedIndex.set(this.panels().length - 1);
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
