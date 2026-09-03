import { ChangeDetectionStrategy, Component } from "@angular/core";
import { BrowserPanel } from "./browser/browser-panel";

@Component({
  selector: "app-root",
  imports: [BrowserPanel],
  template: `
    <main class="workspace">
      @for (browserId of browserIds; track browserId) {
        <app-browser-panel [browserId]="browserId" />
      }
    </main>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly browserIds = ["browser-1", "browser-2"] as const;
}
