import { ChangeDetectionStrategy, Component } from "@angular/core";
import { BrowserPanel } from "./browser/browser-panel";
import { WorkspaceHeader } from "./workspace-header";

@Component({
  selector: "app-root",
  imports: [BrowserPanel, WorkspaceHeader],
  template: `
    <div class="app-shell">
      <app-workspace-header [sessionCount]="ownerIds.length" />

      <main class="workspace" aria-label="Remote Browser Sessions">
        @for (ownerId of ownerIds; track ownerId; let index = $index) {
          <app-browser-panel [ownerId]="ownerId" [position]="index + 1" />
        }
      </main>
    </div>
  `,
  styles: `
    :host { display: block; }
    .app-shell { width: min(100%, 1640px); margin-inline: auto; padding: clamp(12px, 2vw, 32px); }
    app-workspace-header { margin-bottom: clamp(12px, 1.5vw, 20px); }
    .workspace { display: grid; grid-template-columns: minmax(0, 1fr); gap: clamp(16px, 2vw, 28px); }
    @media (max-width: 580px) { .app-shell { padding: 8px; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  // One owner per panel: the backend leases whichever browser is free, so the
  // frontend no longer knows or names the browsers behind it.
  protected readonly ownerIds = [
    crypto.randomUUID(),
    crypto.randomUUID(),
  ] as const;
}
