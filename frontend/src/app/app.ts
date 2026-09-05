import { ChangeDetectionStrategy, Component, signal } from "@angular/core";
import { BrowserPanel } from "./browser/browser-panel";

@Component({
  selector: "app-root",
  imports: [BrowserPanel],
  template: `
    <div class="app-shell">
      <main
        class="browser-stage"
        [attr.data-view]="viewMode()"
        aria-label="Remote Browser Sessions"
      >
        <header class="view-toolbar">
          <div class="view-switcher" role="group" aria-label="Browser-Ansicht">
            <button
              type="button"
              [attr.aria-pressed]="viewMode() === 'focus'"
              (click)="setView('focus')"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <rect x="3" y="4" width="14" height="12" rx="2" />
              </svg>
              Fokus
            </button>
            <button
              type="button"
              [attr.aria-pressed]="viewMode() === 'grid'"
              (click)="setView('grid')"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <rect x="3" y="3" width="5.5" height="5.5" rx="1" />
                <rect x="11.5" y="3" width="5.5" height="5.5" rx="1" />
                <rect x="3" y="11.5" width="5.5" height="5.5" rx="1" />
                <rect x="11.5" y="11.5" width="5.5" height="5.5" rx="1" />
              </svg>
              Kacheln
            </button>
          </div>
          <span class="view-status">
            @if (viewMode() === "focus") {
              Session {{ activeIndex() + 1 }} von {{ ownerIds.length }}
            } @else {
              {{ ownerIds.length }} Sessions im Überblick
            }
          </span>
        </header>

        <div class="browser-gallery">
          @if (viewMode() === "focus") {
            <button
              class="gallery-arrow previous"
              type="button"
              aria-label="Vorherigen Browser anzeigen"
              (click)="previous()"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5-7 7 7 7" /></svg>
            </button>
          }

          <div class="gallery-viewport">
            <div class="browser-track" [style.transform]="trackTransform()">
              @for (ownerId of ownerIds; track ownerId; let index = $index) {
                <app-browser-panel [ownerId]="ownerId" [position]="index + 1" />
              }
            </div>
          </div>

          @if (viewMode() === "focus") {
            <button
              class="gallery-arrow next"
              type="button"
              aria-label="Nächsten Browser anzeigen"
              (click)="next()"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
            </button>
          }
        </div>

        @if (viewMode() === "focus") {
          <nav class="gallery-dots" aria-label="Browser auswählen">
            @for (ownerId of ownerIds; track ownerId; let index = $index) {
              <button
                type="button"
                [class.active]="activeIndex() === index"
                [attr.aria-label]="'Browser ' + (index + 1) + ' anzeigen'"
                [attr.aria-current]="activeIndex() === index ? 'true' : null"
                (click)="show(index)"
              ></button>
            }
          </nav>
        }
      </main>
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    .app-shell {
      width: min(100%, 1640px);
      margin-inline: auto;
      padding: clamp(12px, 2vw, 32px);
    }
    .browser-stage {
      min-width: 0;
    }
    .view-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 12px;
      padding-inline: 4px;
    }
    .view-switcher {
      display: inline-flex;
      gap: 3px;
      padding: 3px;
      background: #10141b;
      border: 1px solid #252d3a;
      border-radius: 10px;
    }
    .view-switcher button {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      min-height: 34px;
      padding: 0 12px;
      color: #7f8a9b;
      font-size: 0.78rem;
      font-weight: 600;
      background: transparent;
      border: 0;
      border-radius: 7px;
      cursor: pointer;
      transition:
        color 180ms ease,
        background 180ms ease,
        box-shadow 180ms ease;
    }
    .view-switcher button[aria-pressed="true"] {
      color: #edf2fb;
      background: #252c37;
      box-shadow: 0 2px 8px rgb(0 0 0 / 22%);
    }
    .view-switcher button:hover:not([aria-pressed="true"]) {
      color: #c4ccda;
      background: #171c24;
    }
    .view-switcher button:focus-visible,
    .gallery-arrow:focus-visible,
    .gallery-dots button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 2px;
    }
    .view-switcher svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.5;
    }
    .view-status {
      color: #707b8d;
      font:
        0.7rem/1 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
    }
    .browser-gallery {
      position: relative;
      min-width: 0;
    }
    .gallery-viewport {
      overflow: hidden;
      min-width: 0;
      border-radius: 14px;
    }
    .browser-track {
      display: flex;
      min-width: 0;
      transition: transform 520ms cubic-bezier(0.22, 1, 0.36, 1);
      will-change: transform;
    }
    .browser-track app-browser-panel {
      flex: 0 0 100%;
      min-width: 0;
    }
    .gallery-arrow {
      position: absolute;
      z-index: 10;
      top: 50%;
      display: grid;
      place-items: center;
      width: 42px;
      height: 56px;
      padding: 0;
      color: #dbe4f4;
      background: rgb(18 23 31 / 86%);
      border: 1px solid #333d4d;
      border-radius: 12px;
      box-shadow: 0 12px 32px rgb(0 0 0 / 35%);
      backdrop-filter: blur(12px);
      cursor: pointer;
      transform: translateY(-50%);
      transition:
        color 180ms ease,
        background 180ms ease,
        transform 180ms ease;
    }
    .gallery-arrow:hover {
      color: #fff;
      background: #263043;
      transform: translateY(-50%) scale(1.04);
    }
    .gallery-arrow.previous {
      left: clamp(8px, 1.4vw, 20px);
    }
    .gallery-arrow.next {
      right: clamp(8px, 1.4vw, 20px);
    }
    .gallery-arrow svg {
      width: 23px;
      height: 23px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.8;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .gallery-dots {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 7px;
      min-height: 30px;
    }
    .gallery-dots button {
      width: 7px;
      height: 7px;
      padding: 0;
      background: #394252;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      transition:
        width 240ms ease,
        background 240ms ease;
    }
    .gallery-dots button.active {
      width: 24px;
      background: #759df3;
    }
    .browser-stage[data-view="grid"] .gallery-viewport {
      overflow: visible;
    }
    .browser-stage[data-view="grid"] .browser-track {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: clamp(14px, 1.5vw, 22px);
      transform: none !important;
      animation: grid-enter 380ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    .browser-stage[data-view="focus"] .gallery-viewport {
      animation: focus-enter 360ms cubic-bezier(0.22, 1, 0.36, 1) both;
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
    @keyframes focus-enter {
      from {
        opacity: 0;
        transform: translateY(6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    @media (max-width: 580px) {
      .app-shell {
        padding: 8px;
      }
      .view-toolbar {
        margin-bottom: 8px;
      }
      .view-status {
        display: none;
      }
      .view-switcher {
        width: 100%;
      }
      .view-switcher button {
        flex: 1;
        justify-content: center;
      }
      .gallery-arrow {
        width: 36px;
        height: 46px;
        border-radius: 10px;
      }
      .gallery-arrow.previous {
        left: 6px;
      }
      .gallery-arrow.next {
        right: 6px;
      }
      .browser-stage[data-view="grid"] .browser-track {
        grid-template-columns: minmax(0, 1fr);
        gap: 14px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .browser-track,
      .view-switcher button,
      .gallery-arrow,
      .gallery-dots button {
        transition: none;
      }
      .browser-stage[data-view] .gallery-viewport,
      .browser-stage[data-view="grid"] .browser-track {
        animation: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  // One owner per panel: the backend leases whichever browser is free, so the
  // frontend no longer knows or names the browsers behind it.
  protected readonly ownerIds = [crypto.randomUUID(), crypto.randomUUID()] as const;
  protected readonly viewMode = signal<"focus" | "grid">("focus");
  protected readonly activeIndex = signal(0);

  protected trackTransform(): string {
    return this.viewMode() === "focus" ? `translateX(-${this.activeIndex() * 100}%)` : "none";
  }

  protected setView(mode: "focus" | "grid"): void {
    this.viewMode.set(mode);
  }

  protected show(index: number): void {
    this.activeIndex.set(index);
  }

  protected previous(): void {
    this.activeIndex.update((index) => (index - 1 + this.ownerIds.length) % this.ownerIds.length);
  }

  protected next(): void {
    this.activeIndex.update((index) => (index + 1) % this.ownerIds.length);
  }
}
