import type {
  BrowserEvent,
  TabResult as BrowserTab,
} from "@browsertunnel/browser-rpc-client";

export interface BrowserViewElements {
  canvas: HTMLCanvasElement;
  addressInput: HTMLInputElement;
  tabList: HTMLDivElement;
  activeTabStatus: HTMLSpanElement;
  cursorStatus: HTMLSpanElement;
  backButton: HTMLButtonElement;
  forwardButton: HTMLButtonElement;
  reloadButton: HTMLButtonElement;
}

interface BrowserViewActions {
  activateTab(tabId: string): Promise<BrowserTab[]>;
  closeTab(tabId: string): Promise<BrowserTab[]>;
  reportError(error: unknown): void;
}

interface NavigationState {
  canGoBack: boolean;
  canGoForward: boolean;
  loading: boolean;
}

export class BrowserView {
  private tabs: BrowserTab[] = [];
  private latestFrame: string | undefined;
  private renderingFrame = false;
  private readonly navigationByTab = new Map<string, NavigationState>();

  constructor(
    private readonly elements: BrowserViewElements,
    private readonly actions: BrowserViewActions,
  ) {}

  applyTabs(tabs: BrowserTab[]): void {
    this.tabs = tabs;
    const active = this.activeTab();
    if (active) {
      this.elements.addressInput.value =
        active.url === "about:blank" ? "" : active.url;
      this.elements.activeTabStatus.textContent =
        `${active.title || "Neuer Tab"} · verbunden`;
    }
    this.applyNavigationControls(
      active ? this.navigationByTab.get(active.id) : undefined,
      active !== undefined,
    );
    this.renderTabs();
  }

  receive(event: BrowserEvent): void {
    if (event.type === "browser.frame") {
      this.latestFrame = event.data;
      void this.renderLatestFrame().catch(this.actions.reportError);
      return;
    }

    if (event.type === "browser.cursor") {
      this.elements.canvas.style.cursor = event.cursor;
      this.elements.cursorStatus.textContent = `cursor: ${event.cursor}`;
      return;
    }

    switch (event.type) {
      case "browser.tabs":
        this.applyTabs(event.tabs);
        break;
      case "browser.navigation":
        this.applyNavigation(event);
        break;
      case "browser.targetCrashed":
        this.elements.activeTabStatus.textContent =
          `Browser abgestürzt · ${event.status}`;
        break;
    }
  }

  private activeTab(): BrowserTab | undefined {
    return this.tabs.find((tab) => tab.active);
  }

  private renderTabs(): void {
    this.elements.tabList.replaceChildren(
      ...this.tabs.map((tab) => this.createTabElement(tab)),
    );
  }

  private createTabElement(tab: BrowserTab): HTMLDivElement {
    const element = document.createElement("div");
    element.className = "browser-tab";
    element.role = "tab";
    element.tabIndex = tab.active ? 0 : -1;
    element.ariaSelected = String(tab.active);

    const favicon = document.createElement("i");
    favicon.ariaHidden = "true";
    const title = document.createElement("span");
    title.textContent = tab.title || "Neuer Tab";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "close-tab";
    close.ariaLabel = `${title.textContent} schließen`;
    close.textContent = "×";

    close.addEventListener("click", (event) => {
      event.stopPropagation();
      void this.actions
        .closeTab(tab.id)
        .then((tabs) => this.applyTabs(tabs))
        .catch(this.actions.reportError);
    });
    element.addEventListener("click", () => {
      void this.actions
        .activateTab(tab.id)
        .then((tabs) => this.applyTabs(tabs))
        .catch(this.actions.reportError);
    });
    element.append(favicon, title, close);
    return element;
  }

  private applyNavigation(
    event: Extract<BrowserEvent, { type: "browser.navigation" }>,
  ): void {
    const navigation = {
      canGoBack: event.canGoBack,
      canGoForward: event.canGoForward,
      loading: event.loading,
    };
    this.navigationByTab.set(event.tabId, navigation);
    this.tabs = this.tabs.map((tab) =>
      tab.id === event.tabId
        ? { ...tab, title: event.title, url: event.url }
        : tab,
    );
    if (this.activeTab()?.id === event.tabId) {
      this.elements.addressInput.value = event.url;
      this.elements.activeTabStatus.textContent =
        `${event.title || "Neuer Tab"} · ${event.loading ? "lädt" : "verbunden"}`;
      this.applyNavigationControls(navigation, true);
    }
    this.renderTabs();
  }

  private applyNavigationControls(
    navigation: NavigationState | undefined,
    hasActiveTab: boolean,
  ): void {
    this.elements.backButton.disabled = !navigation?.canGoBack;
    this.elements.forwardButton.disabled = !navigation?.canGoForward;
    this.elements.reloadButton.disabled = !hasActiveTab;
    const loading = navigation?.loading ?? false;
    this.elements.reloadButton.dataset.loading = String(loading);
    this.elements.reloadButton.ariaLabel = loading
      ? "Laden abbrechen"
      : "Neu laden";
  }

  private async renderLatestFrame(): Promise<void> {
    if (this.renderingFrame) return;
    this.renderingFrame = true;
    try {
      while (this.latestFrame) {
        const encoded = this.latestFrame;
        this.latestFrame = undefined;
        const binary = atob(encoded);
        const bytes = Uint8Array.from(binary, (character) =>
          character.charCodeAt(0),
        );
        const bitmap = await createImageBitmap(
          new Blob([bytes], { type: "image/jpeg" }),
        );
        const { canvas } = this.elements;
        if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
        }
        canvas.getContext("2d")?.drawImage(bitmap, 0, 0);
        bitmap.close();
      }
    } finally {
      this.renderingFrame = false;
    }
  }
}
