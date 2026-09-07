import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { AdminPanel } from "../admin/components/admin-panel";
import { AppViewState } from "./view-mode";
import { BrowserLayout } from "../browser/layouts/browser-layout";
import { ShellViewSwitcher } from "./shell-view-switcher";

@Component({
  selector: "app-shell",
  imports: [AdminPanel, BrowserLayout, ShellViewSwitcher],
  template: `
    <div class="shell">
      <app-shell-view-switcher [view]="views.view()" (viewChange)="views.select($event)" />

      <div class="pane" [class.is-hidden]="views.view() === 'admin'">
        <app-browser-layout [focused]="views.view() === 'focus'" />
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
}
