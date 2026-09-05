import { ChangeDetectionStrategy, Component, computed, signal } from "@angular/core";
import { BrowserCreateTile } from "../components/browser-create-tile";
import { BrowserPanel } from "../components/browser-panel";

@Component({
  selector: "app-browser-layout",
  imports: [BrowserCreateTile, BrowserPanel],
  template: `
    <main class="browser-stage" aria-label="Remote Browser Sessions">
      <div class="browser-grid">
        @for (ownerId of ownerIds(); track ownerId; let index = $index) {
          <app-browser-panel
            [ownerId]="ownerId"
            [position]="index + 1"
            (capacityChange)="handleCapacityChange($event)"
            (leaseFailed)="handleLeaseFailed($event)"
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
export class BrowserLayout {
  protected readonly ownerIds = signal<readonly string[]>([]);
  private readonly remainingCapacity = signal<number | undefined>(undefined);
  private readonly creating = signal(false);
  protected readonly canCreate = computed(
    () => !this.creating() && (this.remainingCapacity() ?? 1) > 0,
  );

  protected createBrowser(): void {
    if (!this.canCreate()) return;
    this.creating.set(true);
    this.ownerIds.update((ownerIds) => [...ownerIds, crypto.randomUUID()]);
  }

  protected handleCapacityChange(remainingCapacity: number): void {
    this.remainingCapacity.set(remainingCapacity);
    this.creating.set(false);
  }

  protected handleLeaseFailed(ownerId: string): void {
    this.ownerIds.update((ownerIds) => ownerIds.filter((id) => id !== ownerId));
    this.creating.set(false);
  }
}
