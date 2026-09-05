import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  input,
  OnDestroy,
  OnInit,
  signal,
  viewChild,
} from "@angular/core";
import { BrowserCanvas } from "./browser-canvas";
import { BrowserSession } from "./browser-session";

@Component({
  selector: "app-browser-panel",
  imports: [BrowserCanvas],
  providers: [BrowserSession],
  template: `
    <section class="browser-panel" [attr.aria-label]="label() + ' Vorschau'">
      <header class="browser-chrome">
        <div class="browser-heading">
          <span>{{ label() }}</span><span class="plane-label">Data Plane</span>
        </div>
        <div class="tab-strip">
          <div class="window-controls" aria-hidden="true"><span></span><span></span><span></span></div>
          <div class="tabs">
            <div class="tab-list" role="tablist" aria-label="Browser-Tabs">
              @for (tab of session.tabs(); track tab.id) {
                <div class="browser-tab" role="tab" [tabIndex]="tab.active ? 0 : -1"
                  [attr.aria-selected]="tab.active" (click)="session.activateTab(tab.id)">
                  <i aria-hidden="true"></i><span>{{ tab.title || 'Neuer Tab' }}</span>
                  <button type="button" class="close-tab"
                    [attr.aria-label]="(tab.title || 'Neuer Tab') + ' schließen'"
                    (click)="$event.stopPropagation(); session.closeTab(tab.id)">×</button>
                </div>
              }
            </div>
            <button class="new-tab" type="button" aria-label="Neuen Tab öffnen" (click)="createTab()">+</button>
          </div>
        </div>
        <div class="browser-bar">
          <nav class="navigation-controls" aria-label="Seitennavigation">
            <button type="button" aria-label="Zurück" [disabled]="!session.navigation()?.canGoBack" (click)="session.back()">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m12.5 4.5-5.5 5 5.5 5" /></svg>
            </button>
            <button type="button" aria-label="Vor" [disabled]="!session.navigation()?.canGoForward" (click)="session.forward()">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7.5 4.5 5.5 5-5.5 5" /></svg>
            </button>
            <button type="button" [disabled]="!session.activeTab()" (click)="session.reloadOrStop()"
              [attr.data-loading]="session.navigation()?.loading ?? false"
              [attr.aria-label]="session.navigation()?.loading ? 'Laden abbrechen' : 'Neu laden'">
              <svg class="reload-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M15.3 7.1A6 6 0 1 0 16 10" /><path d="M15.3 3.8v3.7H12" /></svg>
              <svg class="stop-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 6h8v8H6z" /></svg>
            </button>
          </nav>
          <form class="address-form" (submit)="$event.preventDefault(); navigate()">
            <label class="visually-hidden" [for]="ownerId() + '-url'">URL</label>
            <input #addressInput [id]="ownerId() + '-url'" name="url" type="text" inputmode="url"
              [value]="address()" (input)="updateAddress($event)" placeholder="URL eingeben"
              autocomplete="url" spellcheck="false" />
          </form>
        </div>
      </header>
      <app-browser-canvas />
      <footer class="stream-status">
        <span><i class="status-dot" [class.connected]="session.connection() === 'connected'"></i>{{ session.status() }}</span>
        <span>cursor: {{ session.cursor() }} · 1600 × 900</span>
      </footer>
    </section>
  `,
  host: {
    "(window:pagehide)": "session.release()",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserPanel implements OnInit, OnDestroy {
  readonly ownerId = input.required<string>();
  protected readonly session = inject(BrowserSession);
  protected readonly address = signal("");
  protected readonly label = computed(
    () => this.session.browserId() ?? "Keine Session",
  );
  private readonly addressInput = viewChild<ElementRef<HTMLInputElement>>("addressInput");

  constructor() {
    effect(() => this.address.set(this.session.activeUrl()));
  }

  ngOnInit(): void {
    void this.session.connect(this.ownerId());
  }

  ngOnDestroy(): void {
    void this.session.disconnect();
  }

  protected updateAddress(event: Event): void {
    this.address.set((event.target as HTMLInputElement).value);
  }

  protected navigate(): void {
    const value = this.address().trim();
    if (value) void this.session.navigate(value);
  }

  protected async createTab(): Promise<void> {
    await this.session.createTab();
    this.addressInput()?.nativeElement.focus();
  }

}
