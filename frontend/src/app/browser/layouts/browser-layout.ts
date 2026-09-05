import { ChangeDetectionStrategy, Component, signal } from "@angular/core";
import { BrowserCreateTile } from "../components/browser-create-tile";
import { BrowserGalleryNavigation } from "../components/browser-gallery-navigation";
import { BrowserPanel } from "../components/browser-panel";
import { BrowserViewSwitcher, type BrowserViewMode } from "../components/browser-view-switcher";

@Component({
  selector: "app-browser-layout",
  imports: [BrowserCreateTile, BrowserGalleryNavigation, BrowserPanel, BrowserViewSwitcher],
  template: `
    <div class="app-shell">
      <main
        class="browser-stage"
        [attr.data-view]="viewMode()"
        aria-label="Remote Browser Sessions"
      >
        <app-browser-view-switcher [viewMode]="viewMode()" (viewModeChange)="setView($event)" />

        <div class="browser-gallery">
          <div class="gallery-viewport">
            <div class="browser-track" [style.transform]="trackTransform()">
              @for (ownerId of ownerIds; track ownerId; let index = $index) {
                <app-browser-panel [ownerId]="ownerId" [position]="index + 1" />
              }
              @if (viewMode() === "grid") {
                <app-browser-create-tile />
              }
            </div>
          </div>

          @if (viewMode() === "focus") {
            <app-browser-gallery-navigation
              [items]="ownerIds"
              [activeIndex]="activeIndex()"
              (previous)="previous()"
              (next)="next()"
              (show)="show($event)"
            />
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
    .browser-stage,
    .browser-gallery,
    .gallery-viewport,
    .browser-track {
      min-width: 0;
    }
    .browser-gallery {
      position: relative;
    }
    .gallery-viewport {
      overflow: hidden;
      border-radius: 14px;
    }
    .browser-track {
      display: flex;
      transition: transform 520ms cubic-bezier(0.22, 1, 0.36, 1);
      will-change: transform;
    }
    .browser-track app-browser-panel {
      flex: 0 0 100%;
      min-width: 0;
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
        padding: 4px 8px 14px;
      }
      .browser-stage[data-view="grid"] .browser-track {
        grid-template-columns: minmax(0, 1fr);
        gap: 14px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .browser-track {
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
export class BrowserLayout {
  protected readonly ownerIds = [crypto.randomUUID(), crypto.randomUUID()] as const;
  protected readonly viewMode = signal<BrowserViewMode>("focus");
  protected readonly activeIndex = signal(0);

  protected trackTransform(): string {
    return this.viewMode() === "focus" ? `translateX(-${this.activeIndex() * 100}%)` : "none";
  }

  protected setView(mode: BrowserViewMode): void {
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
