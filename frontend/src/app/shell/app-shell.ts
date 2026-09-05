import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from "@angular/core";
import { AdminPanel } from "../admin/components/admin-panel";
import { AppViewState } from "./view-mode";
import { BrowserLayout } from "../browser/layouts/browser-layout";
import { ShellViewSwitcher } from "./shell-view-switcher";
import type { BrowserViewMode } from "../browser/layouts/browser-layout";

@Component({
  selector: "app-shell",
  imports: [AdminPanel, BrowserLayout, ShellViewSwitcher],
  template: `
    <div class="shell">
      <app-shell-view-switcher [view]="views.view()" (viewChange)="views.select($event)" />

      <!--
        Both tabs stay mounted: tearing the gallery down would close every live
        session, so looking at the admin view must not cost the browsers it lists.
      -->
      <div class="pane" [class.is-hidden]="views.view() === 'admin'">
        <app-browser-layout [view]="galleryView()" />
      </div>
      <div class="pane" [class.is-hidden]="views.view() !== 'admin'">
        <app-admin-panel [active]="views.view() === 'admin'" />
      </div>
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    .shell {
      width: 100%;
      padding: 6px clamp(10px, 1.4vw, 26px) clamp(16px, 2vw, 32px);
    }
    .pane.is-hidden {
      display: none;
    }
    @media (max-width: 580px) {
      .shell {
        padding: 4px 8px 14px;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppShell {
  protected readonly views = inject(AppViewState);
  /** Which gallery layout to return to when the admin tab is closed again. */
  private readonly lastGalleryView = signal<BrowserViewMode>("grid");
  protected readonly galleryView = computed(() => this.lastGalleryView());

  constructor() {
    effect(() => {
      const view = this.views.view();
      if (view !== "admin") this.lastGalleryView.set(view);
    });
  }
}
