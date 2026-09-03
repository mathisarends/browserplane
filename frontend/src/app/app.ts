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
  protected readonly browserIds = [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
  ] as const;
}
