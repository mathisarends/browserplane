import type { BrowserEvent, TabResult } from "@browsertunnel/browser-rpc-client/models";
import { computed, signal } from "@lit-labs/signals";
export interface NavigationState {
  readonly canGoBack: boolean;
  readonly canGoForward: boolean;
  readonly loading: boolean;
  readonly faviconUrl?: string | null;
}
export interface BrowserTabState extends TabResult {
  readonly faviconUrl?: string | null;
}
const BLANK_PAGE = "about:blank";
export class BrowserPageState {
  private readonly tabsState = signal<readonly BrowserTabState[]>([]);
  private readonly navigationByTab = signal<ReadonlyMap<string, NavigationState>>(new Map());
  private readonly cursorState = signal("default");
  readonly tabs = this.tabsState;
  readonly cursor = this.cursorState;
  readonly activeTab = computed(() => this.tabs.get().find((tab) => tab.active));
  readonly navigation = computed(() => {
    const tabId = this.activeTab.get()?.id;
    return tabId ? this.navigationByTab.get().get(tabId) : undefined;
  });
  readonly activeUrl = computed(() => {
    const url = this.activeTab.get()?.url;
    return !url || url === BLANK_PAGE ? "" : url;
  });
  setTabs(tabs: readonly BrowserTabState[]): void {
    this.tabsState.set(tabs);
  }
  reset(): void {
    this.tabsState.set([]);
    this.navigationByTab.set(new Map());
    this.cursorState.set("default");
  }
  apply(event: BrowserEvent): void {
    switch (event.type) {
      case "browser.cursor":
        this.cursorState.set(event.cursor);
        break;
      case "browser.tabs":
        this.tabsState.set(event.tabs);
        break;
      case "browser.navigation":
        this.navigationByTab.set(
          ((current) => new Map(current).set(event.tabId, event))(this.navigationByTab.get()),
        );
        this.tabsState.set(
          ((tabs) =>
            tabs.map((tab) =>
              tab.id === event.tabId
                ? { ...tab, title: event.title, url: event.url, faviconUrl: event.faviconUrl }
                : tab,
            ))(this.tabsState.get()),
        );
        break;
      default:
        break;
    }
  }
}
export function pageFailure(event: BrowserEvent): string | undefined {
  if (event.type === "browser.navigation") return event.error ?? undefined;
  if (event.type === "browser.targetCrashed") return `Browser crashed · ${event.status}`;
  return undefined;
}
