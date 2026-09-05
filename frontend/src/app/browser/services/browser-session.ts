import { computed, Injectable, signal } from "@angular/core";
import {
  closeSession,
  openSession,
  type openSessionResponse,
  type SessionResponse,
} from "@browsertunnel/backend-client";
import {
  BackendBrowserClient,
  WebSocketRpcTransport,
  type BrowserEvent,
  type KeyParams,
  type MouseParams,
  type ScrollParams,
  type TabResult,
} from "@browsertunnel/browser-rpc-client";

export interface NavigationState {
  readonly canGoBack: boolean;
  readonly canGoForward: boolean;
  readonly loading: boolean;
  readonly faviconUrl?: string | null;
}

export interface BrowserTabState extends TabResult {
  readonly faviconUrl?: string | null;
}

export type ConnectionState = "connecting" | "connected" | "disconnected";

/**
 * A backstop only: the backend releases the session when the tunnel socket
 * closes, so this covers a session whose socket never came up at all.
 */
const SESSION_TTL_SECONDS = 600;
const DUCKDUCKGO_SEARCH_URL = "https://duckduckgo.com/?q=";

/** Signal-based UI facade around the generated RPC client. */
@Injectable()
export class BrowserSession {
  private transport?: WebSocketRpcTransport;
  private client?: BackendBrowserClient;
  private screencast?: WebSocket;
  private readonly sessionState = signal<SessionResponse | undefined>(undefined);
  private readonly tabsState = signal<readonly BrowserTabState[]>([]);
  private readonly navigationState = signal(new Map<string, NavigationState>());
  private readonly connectionState = signal<ConnectionState>("disconnected");
  private readonly errorState = signal<string | undefined>(undefined);
  private readonly frameState = signal<Blob | undefined>(undefined);
  private readonly cursorState = signal("default");

  readonly tabs = this.tabsState.asReadonly();
  readonly connection = this.connectionState.asReadonly();
  readonly error = this.errorState.asReadonly();
  readonly frame = this.frameState.asReadonly();
  readonly cursor = this.cursorState.asReadonly();
  readonly browserId = computed(() => this.sessionState()?.browser_id);
  readonly sessionId = computed(() => this.sessionState()?.id);
  readonly activeTab = computed(() => this.tabs().find((tab) => tab.active));
  readonly activeUrl = computed(() => {
    const url = this.activeTab()?.url;
    return url === "about:blank" ? "" : (url ?? "");
  });
  readonly navigation = computed(() => {
    const tabId = this.activeTab()?.id;
    return tabId ? this.navigationState().get(tabId) : undefined;
  });
  readonly status = computed(() => {
    const error = this.error();
    if (error) return `Error · ${error}`;
    if (this.connection() === "connecting") return "Connecting";
    if (this.connection() === "disconnected") return "Not connected";
    const tab = this.activeTab();
    if (!tab) return "Stream waiting";
    return `${tab.title || "New tab"} · ${this.navigation()?.loading ? "loading" : "connected"}`;
  });

  async connect(ownerId: string): Promise<number | undefined> {
    this.connectionState.set("connecting");
    this.errorState.set(undefined);
    try {
      const response = await openSession({
        owner_id: ownerId,
        ttl_seconds: SESSION_TTL_SECONDS,
      });
      if (response.status !== 201) throw new Error(openSessionError(response));
      const session = response.data;
      // A session that was just opened is active, so it carries both paths;
      // a suspended one holds no browser and leaves them empty.
      if (!session.tunnel_path || !session.screencast_path) {
        throw new Error("The session does not contain a browser");
      }
      this.sessionState.set(session);
      this.transport = new WebSocketRpcTransport(socketUrl(session.tunnel_path));
      this.client = new BackendBrowserClient(this.transport);
      await this.transport.connect();
      await this.connectScreencast(socketUrl(session.screencast_path));
      this.connectionState.set("connected");
      void this.receiveNotifications();
      this.tabsState.set((await this.client.browser.tab.list()).tabs);
      return response.data.remaining_capacity;
    } catch (error) {
      await this.disconnect();
      this.reportError(error);
      return undefined;
    }
  }

  async disconnect(): Promise<void> {
    this.connectionState.set("disconnected");
    const client = this.client;
    const screencast = this.screencast;
    const session = this.sessionState();
    this.client = undefined;
    this.transport = undefined;
    this.screencast = undefined;
    this.sessionState.set(undefined);
    this.frameState.set(undefined);
    screencast?.close();
    await client?.close().catch(() => undefined);
    // The lease would expire on its own, but releasing it hands the browser
    // back to the pool right away.
    if (session) await closeSession(session.id).catch(() => undefined);
  }

  navigate(value: string): Promise<void> {
    const url = resolveNavigationTarget(value);
    return this.run((client) => client.browser.nav.navigate({ url }));
  }

  back(): Promise<void> {
    return this.run((client) => client.browser.nav.back());
  }

  forward(): Promise<void> {
    return this.run((client) => client.browser.nav.forward());
  }

  reloadOrStop(): Promise<void> {
    return this.run((client) =>
      this.navigation()?.loading ? client.browser.nav.stop() : client.browser.nav.reload(),
    );
  }

  createTab(): Promise<void> {
    return this.run(async (client) => {
      this.tabsState.set((await client.browser.tab.create({ url: "about:blank" })).tabs);
    });
  }

  refreshTabs(): Promise<void> {
    return this.run(async (client) => {
      this.tabsState.set((await client.browser.tab.list()).tabs);
    });
  }

  activateTab(tabId: string): Promise<void> {
    return this.run(async (client) => {
      this.tabsState.set((await client.browser.tab.activate({ tabId })).tabs);
    });
  }

  closeTab(tabId: string): Promise<void> {
    return this.run(async (client) => {
      this.tabsState.set((await client.browser.tab.close({ tabId })).tabs);
    });
  }

  sendMouse(params: MouseParams): Promise<void> {
    return this.run((client) => client.browser.input.mouse(params));
  }

  sendScroll(params: ScrollParams): Promise<void> {
    return this.run((client) => client.browser.input.scroll(params));
  }

  sendKey(params: KeyParams): Promise<void> {
    return this.run((client) => client.browser.input.key(params));
  }

  paste(text: string): Promise<void> {
    return this.run((client) => client.browser.input.paste({ text }));
  }

  copy(): Promise<void> {
    return this.run(async (client) => {
      const { text } = await client.browser.clipboard.copy();
      if (text) await navigator.clipboard.writeText(text);
    });
  }

  reportError(error: unknown): void {
    this.errorState.set(error instanceof Error ? error.message : String(error));
  }

  private async run(action: (client: BackendBrowserClient) => Promise<void>): Promise<void> {
    if (!this.client) {
      // Input keeps arriving after a failed connect; don't let its aftermath
      // overwrite the error that actually explains the missing connection.
      if (!this.error()) this.reportError("RPC connection is unavailable");
      return;
    }
    try {
      await action(this.client);
      this.errorState.set(undefined);
    } catch (error) {
      this.reportError(error);
    }
  }

  private async receiveNotifications(): Promise<void> {
    const client = this.client;
    if (!client) return;
    try {
      for await (const notification of client.notifications()) {
        if (client !== this.client) return;
        this.receive(notification.params);
      }
    } catch (error) {
      if (client === this.client) this.reportError(error);
    }
  }

  private receive(event: BrowserEvent): void {
    switch (event.type) {
      case "browser.cursor":
        this.cursorState.set(event.cursor);
        break;
      case "browser.tabs":
        this.tabsState.set(event.tabs);
        break;
      case "browser.navigation":
        this.navigationState.update((current) => {
          const next = new Map(current);
          next.set(event.tabId, event);
          return next;
        });
        this.tabsState.update((tabs) =>
          tabs.map((tab) =>
            tab.id === event.tabId
              ? {
                  ...tab,
                  title: event.title,
                  url: event.url,
                  faviconUrl: event.faviconUrl,
                }
              : tab,
          ),
        );
        if (event.error) this.errorState.set(event.error);
        break;
      case "browser.targetCrashed":
        this.errorState.set(`Browser crashed · ${event.status}`);
        break;
      case "browser.targetDetached":
        break;
    }
  }

  private async connectScreencast(url: URL): Promise<void> {
    const socket = new WebSocket(url);
    this.screencast = socket;
    await socketOpened(socket);
    socket.addEventListener("message", (event) => {
      if (socket === this.screencast && event.data instanceof Blob) {
        this.frameState.set(event.data);
      }
    });
    socket.addEventListener("close", () => {
      if (socket === this.screencast) {
        this.reportError("Screencast connection was disconnected");
      }
    });
  }
}

/** Resolve address-bar input like a browser omnibox would. */
export function resolveNavigationTarget(value: string): string {
  const input = value.trim();

  if (isLikelyAddress(input)) {
    return input.startsWith("//") ? `https:${input}` : `https://${input}`;
  }

  if (/^[a-z][a-z\d+.-]*:/i.test(input)) return input;

  return `${DUCKDUCKGO_SEARCH_URL}${encodeURIComponent(input)}`;
}

function isLikelyAddress(value: string): boolean {
  if (!value || /\s/.test(value)) return false;

  try {
    const url = new URL(value.startsWith("//") ? `https:${value}` : `https://${value}`);
    const hostname = url.hostname.toLowerCase();
    return (
      !url.username &&
      !url.password &&
      (hostname === "localhost" || hostname.includes(".") || /^\[[\da-f:]+\]$/i.test(hostname))
    );
  } catch {
    return false;
  }
}

/** Turn a backend-relative live-traffic path into a WebSocket URL. */
function socketUrl(path: string): URL {
  const url = new URL(path, window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url;
}

function socketOpened(socket: WebSocket): Promise<void> {
  return new Promise((resolve, reject) => {
    socket.addEventListener("open", () => resolve(), { once: true });
    socket.addEventListener("error", () => reject(new Error("Screencast connection failed")), {
      once: true,
    });
    socket.addEventListener(
      "close",
      () => reject(new Error("Screencast connection was disconnected")),
      { once: true },
    );
  });
}

function openSessionError(response: openSessionResponse): string {
  if (response.status === 503) return response.data.message;
  return `Session could not be opened (${response.status})`;
}
