import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  OnDestroy,
  OnInit,
  signal,
  viewChild,
} from "@angular/core";
import { BrowserCanvas } from "./browser-canvas";
import { BrowserNavigationBar } from "./browser-navigation-bar";
import { BrowserSession } from "./browser-session";
import { BrowserSessionHeader } from "./browser-session-header";
import { BrowserStateToolbar } from "./browser-state-toolbar";
import { BrowserTabStrip } from "./browser-tab-strip";

@Component({
  selector: "app-browser-panel",
  imports: [
    BrowserCanvas,
    BrowserNavigationBar,
    BrowserSessionHeader,
    BrowserStateToolbar,
    BrowserTabStrip,
  ],
  providers: [BrowserSession],
  template: `
    <section class="browser-panel" [attr.aria-label]="label() + ' Vorschau'">
      <header class="browser-chrome">
        <app-browser-session-header
          [position]="position()"
          [label]="label()"
          [connection]="session.connection()"
        />
        <app-browser-state-toolbar [position]="position()" />
        <app-browser-tab-strip
          [tabs]="session.tabs()"
          (activate)="session.activateTab($event)"
          (close)="session.closeTab($event)"
          (create)="createTab()"
        />
        <app-browser-navigation-bar
          #navigationBar
          [ownerId]="ownerId()"
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
      <footer class="stream-status">
        <span
          ><i class="status-dot" [class.connected]="session.connection() === 'connected'"></i
          >{{ session.status() }}</span
        >
        <span class="stream-meta">cursor: {{ session.cursor() }} · 1600 × 900</span>
      </footer>
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
    .stream-status {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      min-height: 37px;
      padding: 8px 14px;
      color: #7f8998;
      font:
        0.69rem/1.25 ui-monospace,
        SFMono-Regular,
        Consolas,
        monospace;
      background: #11151c;
      border-top: 1px solid #252a33;
    }
    .stream-status span:first-child {
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 7px;
    }
    .status-dot {
      display: inline-block;
      flex: none;
      width: 7px;
      height: 7px;
      background: #e5a84b;
      border-radius: 50%;
    }
    .status-dot.connected {
      background: #61c454;
    }
    .stream-meta {
      flex: none;
      color: #626d7f;
    }
    @media (max-width: 580px) {
      .browser-panel {
        border-radius: 10px;
      }
      .stream-status {
        min-height: 34px;
        padding: 7px 10px;
      }
      .stream-status span:first-child {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .stream-meta {
        display: none;
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
  readonly ownerId = input.required<string>();
  readonly position = input.required<number>();
  protected readonly session = inject(BrowserSession);
  protected readonly address = signal("");
  protected readonly label = computed(() => this.session.browserId() ?? "Keine Session");
  private readonly navigationBar = viewChild<BrowserNavigationBar>("navigationBar");

  constructor() {
    effect(() => this.address.set(this.session.activeUrl()));
  }

  ngOnInit(): void {
    void this.session.connect(this.ownerId());
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
}
