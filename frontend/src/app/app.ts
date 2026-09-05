import { ChangeDetectionStrategy, Component } from "@angular/core";
import { BrowserPanel } from "./browser/browser-panel";

@Component({
  selector: "app-root",
  imports: [BrowserPanel],
  template: `
    <main class="workspace">
      @for (ownerId of ownerIds; track ownerId) {
        <app-browser-panel [ownerId]="ownerId" />
      }
    </main>
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
