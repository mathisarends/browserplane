import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  OnDestroy,
  OnInit,
  output,
  signal,
  viewChild,
} from "@angular/core";
import { BrowserCanvas } from "./browser-canvas";
import { BrowserNavigationBar } from "./browser-navigation-bar";
import { BrowserSession } from "../services/browser-session";
import { BrowserStateToolbar } from "./browser-state-toolbar";
import { BrowserTabStrip } from "./browser-tab-strip";

@Component({
  selector: "app-browser-panel",
  imports: [BrowserCanvas, BrowserNavigationBar, BrowserStateToolbar, BrowserTabStrip],
  providers: [BrowserSession],
  template: `
    <section class="browser-panel" [attr.aria-label]="label() + ' preview'">
      <header class="browser-chrome">
        <app-browser-tab-strip
          [tabs]="session.tabs()"
          (activate)="session.activateTab($event)"
          (close)="session.closeTab($event)"
          (create)="createTab()"
        />
        <app-browser-navigation-bar
          #navigationBar
          [panelId]="panelId()"
          [address]="address()"
          [navigation]="session.navigation()"
          [hasActiveTab]="!!session.activeTab()"
          (addressChange)="address.set($event)"
          (navigate)="navigate()"
          (back)="session.back()"
          (forward)="session.forward()"
          (reloadOrStop)="session.reloadOrStop()"
        />
      </header>
      <app-browser-canvas />
      <app-browser-state-toolbar [position]="position()" />
    </section>
  `,
  styles: `
    :host {
      display: block;
    }
    .browser-panel {
      overflow: hidden;
      background: #11151c;
      border: 1px solid #252d3a;
      border-radius: 14px;
      box-shadow: 0 28px 80px rgb(0 0 0 / 34%);
    }
    .browser-chrome {
      background: linear-gradient(180deg, #1a202a, #171c24);
    }
    @media (max-width: 580px) {
      .browser-panel {
        border-radius: 10px;
      }
    }
    @media (prefers-reduced-motion: no-preference) {
      .browser-panel {
        animation: panel-enter 420ms both;
      }
      @keyframes panel-enter {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserPanel implements OnInit, OnDestroy {
  readonly panelId = input.required<string>();
  /** Set when the panel takes a session over instead of leasing a browser. */
  readonly sessionId = input<string>();
  readonly position = input.required<number>();
  readonly capacityChange = output<number>();
  readonly sessionLost = output<string>();
  protected readonly session = inject(BrowserSession);
  protected readonly address = signal("");
  protected readonly label = computed(() => this.session.browserId() ?? "No session");
  private readonly navigationBar = viewChild<BrowserNavigationBar>("navigationBar");

  constructor() {
    effect(() => this.address.set(this.session.activeUrl()));
  }

  ngOnInit(): void {
    void this.connect();
  }

  ngOnDestroy(): void {
    void this.session.disconnect();
  }

  protected navigate(): void {
    const value = this.address().trim();
    if (value) void this.session.navigate(value);
  }

  protected async createTab(): Promise<void> {
    await this.session.createTab();
    this.navigationBar()?.focusAddress();
  }

  private async connect(): Promise<void> {
    const sessionId = this.sessionId();
    if (sessionId) {
      // Taking a session over leaves the pool as it was, so there is no
      // capacity news to report.
      if (!(await this.session.attach(sessionId))) this.sessionLost.emit(this.panelId());
      return;
    }
    const remainingCapacity = await this.session.open();
    if (remainingCapacity === undefined) {
      this.sessionLost.emit(this.panelId());
      return;
    }
    this.capacityChange.emit(remainingCapacity);
  }
}
