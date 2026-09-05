import { ChangeDetectionStrategy, Component, computed, input, signal } from "@angular/core";
import { BrowserCreateTile } from "../components/browser-create-tile";
import { BrowserGalleryNavigation } from "../components/browser-gallery-navigation";
import { BrowserPanel } from "../components/browser-panel";

/** The two ways the gallery can lay its sessions out. */
export type BrowserViewMode = "grid" | "focus";

@Component({
  selector: "app-browser-layout",
  imports: [BrowserCreateTile, BrowserGalleryNavigation, BrowserPanel],
  template: `
    <main class="browser-stage" [attr.data-view]="view()" aria-label="Remote Browser Sessions">
      <div class="browser-gallery">
        <div class="gallery-viewport">
          <div class="browser-track" [style.transform]="trackTransform()">
            @for (ownerId of ownerIds(); track ownerId; let index = $index) {
              <app-browser-panel
                [ownerId]="ownerId"
                [position]="index + 1"
                (capacityChange)="handleCapacityChange($event)"
                (leaseFailed)="handleLeaseFailed($event)"
              />
            }
            @if (canCreate() && (view() === "grid" || ownerIds().length === 0)) {
              <app-browser-create-tile (create)="createBrowser()" />
            }
          </div>
        </div>

        @if (view() === "focus" && ownerIds().length > 0) {
          <app-browser-gallery-navigation
            [items]="ownerIds()"
            [activeIndex]="activeIndex()"
            (previous)="previous()"
            (next)="next()"
            (show)="show($event)"
          />
        }
      </div>
    </main>
  `,
  styles: `
    :host {
      display: block;
    }
    .browser-stage,
    .browser-gallery,
    .gallery-viewport,
    .browser-track {
      min-width: 0;
    }
    .browser-stage {
      width: min(100%, 1640px);
      margin-inline: auto;
    }
    .browser-stage[data-view="grid"] {
      width: min(100%, 2560px);
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
    .browser-track app-browser-panel,
    .browser-track app-browser-create-tile {
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
  readonly view = input.required<BrowserViewMode>();
  protected readonly ownerIds = signal<readonly string[]>([]);
  protected readonly activeIndex = signal(0);
  private readonly remainingCapacity = signal<number | undefined>(undefined);
  private readonly creating = signal(false);
  protected readonly canCreate = computed(
    () => !this.creating() && (this.remainingCapacity() ?? 1) > 0,
  );

  protected createBrowser(): void {
    if (!this.canCreate()) return;
    const nextIndex = this.ownerIds().length;
    this.creating.set(true);
    this.ownerIds.update((ownerIds) => [...ownerIds, crypto.randomUUID()]);
    this.activeIndex.set(nextIndex);
  }

  protected handleCapacityChange(remainingCapacity: number): void {
    this.remainingCapacity.set(remainingCapacity);
    this.creating.set(false);
  }

  protected handleLeaseFailed(ownerId: string): void {
    this.ownerIds.update((ownerIds) => ownerIds.filter((id) => id !== ownerId));
    this.activeIndex.update((index) => Math.max(0, Math.min(index, this.ownerIds().length - 1)));
    this.creating.set(false);
  }

  protected trackTransform(): string {
    return this.view() === "focus" ? `translateX(-${this.activeIndex() * 100}%)` : "none";
  }

  protected show(index: number): void {
    this.activeIndex.set(index);
  }

  protected previous(): void {
    const length = this.ownerIds().length;
    this.activeIndex.update((index) => (index - 1 + length) % length);
  }

  protected next(): void {
    const length = this.ownerIds().length;
    this.activeIndex.update((index) => (index + 1) % length);
  }
}
