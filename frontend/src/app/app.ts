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
              Fokus
            </button>
            <button
              type="button"
              [attr.aria-pressed]="viewMode() === 'grid'"
              (click)="setView('grid')"
            >
              Kacheln
            </button>
          </div>
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
              @if (viewMode() === "grid") {
                <section class="browser-create-tile" aria-label="Neuen Browser erstellen">
                  <button type="button">
                    <span class="create-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <path d="M12 5v14M5 12h14" />
                      </svg>
                    </span>
                    <span class="create-copy">
                      <strong>Neuen Browser erstellen</strong>
                      <small>Weitere Browser-Session hinzufügen</small>
                    </span>
                  </button>
                </section>
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
        </div>
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
      padding: 6px clamp(10px, 2vw, 32px) clamp(16px, 2vw, 32px);
    }
    .browser-stage {
      min-width: 0;
    }
    .view-toolbar {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-bottom: 8px;
    }
    .view-switcher {
      display: inline-flex;
      width: 216px;
      padding: 2px;
      background: #191a1d;
      border: 1px solid #2b2d31;
      border-radius: 999px;
      box-shadow:
        inset 0 1px 0 rgb(255 255 255 / 3%),
        0 8px 24px rgb(0 0 0 / 18%);
    }
    .view-switcher button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 1;
      min-height: 31px;
      padding: 0 16px;
      color: #a8acb4;
      font-size: 0.8rem;
      font-weight: 600;
      background: transparent;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      transition:
        color 180ms ease,
        background 180ms ease,
        box-shadow 180ms ease;
    }
    .view-switcher button[aria-pressed="true"] {
      color: #f4f5f7;
      background: #282a2e;
      box-shadow:
        inset 0 1px 0 rgb(255 255 255 / 4%),
        0 1px 4px rgb(0 0 0 / 28%);
    }
    .view-switcher button:hover:not([aria-pressed="true"]) {
      color: #d7d9de;
    }
    .view-switcher button:focus-visible,
    .gallery-arrow:focus-visible,
    .gallery-dots button:focus-visible,
    .browser-create-tile button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 2px;
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
      position: absolute;
      z-index: 10;
      bottom: 38px;
      left: 50%;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 7px;
      min-height: 26px;
      padding: 0 11px;
      background: rgb(12 16 22 / 76%);
      border: 1px solid rgb(68 79 96 / 58%);
      border-radius: 999px;
      box-shadow: 0 8px 24px rgb(0 0 0 / 28%);
      backdrop-filter: blur(10px);
      transform: translateX(-50%);
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
    .browser-create-tile {
      display: grid;
      min-width: 0;
      aspect-ratio: 4 / 3;
      overflow: hidden;
      background: rgb(13 15 19 / 68%);
      border: 1px dashed #2c3037;
      border-radius: 14px;
    }
    .browser-create-tile button {
      display: grid;
      place-content: center;
      justify-items: center;
      gap: 12px;
      width: 100%;
      padding: 20px;
      color: #aeb3bd;
      background: transparent;
      border: 0;
      cursor: pointer;
      transition:
        color 180ms ease,
        background 180ms ease;
    }
    .browser-create-tile button:hover {
      color: #f0f1f3;
      background: rgb(255 255 255 / 2.5%);
    }
    .create-icon {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      color: #c5c8cf;
      background: #1b1d22;
      border: 1px solid #32353c;
      border-radius: 999px;
      box-shadow: inset 0 1px 0 rgb(255 255 255 / 4%);
    }
    .create-icon svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.6;
      stroke-linecap: round;
    }
    .create-copy {
      display: grid;
      gap: 4px;
      text-align: center;
    }
    .create-copy strong {
      color: inherit;
      font-size: 0.82rem;
      font-weight: 650;
    }
    .create-copy small {
      color: #686e79;
      font-size: 0.68rem;
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
        padding: 4px 8px 14px;
      }
      .view-toolbar {
        margin-bottom: 6px;
      }
      .view-switcher {
        width: 208px;
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
      .gallery-dots {
        bottom: 36px;
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
      .gallery-dots button,
      .browser-create-tile button {
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
