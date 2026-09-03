import "./style.css";
import {
  BrowserTunnelClient,
  WebSocketRpcTransport,
} from "@browsertunnel/browser-rpc-client";
import { BrowserInput } from "./browser-input";
import { BrowserView, type BrowserViewElements } from "./browser-view";

const BROWSERS = ["browser-1", "browser-2"] as const;

function requiredElement<T extends Element>(
  root: ParentNode,
  selector: string,
): T {
  const element = root.querySelector<T>(selector);
  if (!element) throw new Error(`Required element not found: ${selector}`);
  return element;
}

const workspace = requiredElement<HTMLElement>(document, "#browser-workspace");
const template = requiredElement<HTMLTemplateElement>(
  document,
  "#browser-panel-template",
);

for (const browserId of BROWSERS) mountBrowser(browserId);

function mountBrowser(browserId: string): void {
  const fragment = template.content.cloneNode(true) as DocumentFragment;
  const panel = requiredElement<HTMLElement>(fragment, ".browser-panel");
  panel.dataset.browserId = browserId;
  panel.ariaLabel = `${browserId} Vorschau`;
  requiredElement<HTMLElement>(panel, ".browser-identity").textContent = browserId;
  workspace.append(fragment);

  const elements: BrowserViewElements = {
    canvas: requiredElement(panel, ".browser-canvas"),
    addressInput: requiredElement(panel, ".address-input"),
    tabList: requiredElement(panel, ".tab-list"),
    activeTabStatus: requiredElement(panel, ".active-tab-status"),
    cursorStatus: requiredElement(panel, ".cursor-status"),
    backButton: requiredElement(panel, ".nav-back"),
    forwardButton: requiredElement(panel, ".nav-forward"),
    reloadButton: requiredElement(panel, ".nav-reload"),
  };
  const addressForm = requiredElement<HTMLFormElement>(panel, ".address-form");
  const newTabButton = requiredElement<HTMLButtonElement>(panel, ".new-tab");

  const reportError = (error: unknown): void => {
    const message = error instanceof Error ? error.message : String(error);
    elements.activeTabStatus.textContent = `Fehler · ${message}`;
  };

  const socketUrl = new URL(`/api/browsers/${browserId}/ws`, window.location.href);
  socketUrl.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socketTransport = new WebSocketRpcTransport(socketUrl);
  const client = new BrowserTunnelClient(socketTransport);
  const view = new BrowserView(elements, {
    activateTab: async (tabId) =>
      (await client.browser.tab.activate({ tabId })).tabs,
    closeTab: async (tabId) => (await client.browser.tab.close({ tabId })).tabs,
    reportError,
  });

  new BrowserInput(elements.canvas, client, reportError).attach();

  addressForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = elements.addressInput.value.trim();
    if (!value) return;
    void client.browser.nav.navigate({ url: normalizeUrl(value) }).catch(reportError);
  });

  newTabButton.addEventListener("click", () => {
    void client.browser.tab
      .create({ url: "about:blank" })
      .then((result) => {
        view.applyTabs(result.tabs);
        elements.addressInput.focus();
      })
      .catch(reportError);
  });

  elements.backButton.addEventListener("click", () => {
    void client.browser.nav.back().catch(reportError);
  });
  elements.forwardButton.addEventListener("click", () => {
    void client.browser.nav.forward().catch(reportError);
  });
  elements.reloadButton.addEventListener("click", () => {
    const request =
      elements.reloadButton.dataset.loading === "true"
        ? client.browser.nav.stop()
        : client.browser.nav.reload();
    void request.catch(reportError);
  });

  void connect();

  async function connect(): Promise<void> {
    try {
      await socketTransport.connect();
      elements.activeTabStatus.textContent = `${browserId} · Stream wartet`;
      void receiveNotifications().catch(reportError);
      view.applyTabs((await client.browser.tab.list()).tabs);
    } catch (error) {
      reportError(error);
    }
  }

  async function receiveNotifications(): Promise<void> {
    for await (const notification of client.notifications()) {
      view.receive(notification.params);
    }
  }
}

function normalizeUrl(value: string): string {
  return /^[a-z][a-z\d+.-]*:/i.test(value) ? value : `https://${value}`;
}
