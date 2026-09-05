import { ChangeDetectionStrategy, Component } from "@angular/core";
import { BrowserLayout } from "./browser/layouts/browser-layout";

@Component({
  selector: "app-root",
  imports: [BrowserLayout],
  template: `<app-browser-layout />`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {}
