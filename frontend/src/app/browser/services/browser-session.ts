import { computed, inject, Injectable, signal } from "@angular/core";
import {
  cancelSessionRequest,
  closeSession,
  getSessionRequest,
  getSession,
  openSession,
  resumeSession,
  type openSessionResponse,
  type RequestStatus,
  type SessionResponse,
} from "@browsertunnel/backend-client";
import { ClientIdentity } from "./client-identity";
import {
  DirtyRectangleScreencast,
  type DirtyRectangleEvent,
  type DirtyRectangleScreencastState,
} from "./dirty-rectangle-screencast";
import { ScreencastModeState, type ScreencastMode } from "./screencast-mode";
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

/** How long one request may wait for browser capacity. */
const SESSION_REQUEST_TIMEOUT_SECONDS = 60;
const DUCKDUCKGO_SEARCH_URL = "https://duckduckgo.com/?q=";

interface PendingSessionRequest {
  readonly id: string;
  readonly controller: AbortController;
}

/** Signal-based UI facade around the generated RPC client. */
@Injectable()
export class BrowserSession {
  private readonly identity = inject(ClientIdentity);
  private readonly screencastMode = inject(ScreencastModeState);
  private transport?: WebSocketRpcTransport;
  private client?: BackendBrowserClient;
  private screencast?: WebSocket;
  private dirtyRectangles?: DirtyRectangleScreencast;
  /** Canvas work waiting to be drawn, drained in order by the canvas. */
  private readonly dirtyRectangleQueue: DirtyRectangleEvent[] = [];
  private pendingRequest?: PendingSessionRequest;
  private readonly sessionState = signal<SessionResponse | undefined>(undefined);
  private readonly tabsState = signal<readonly BrowserTabState[]>([]);
  private readonly navigationState = signal(new Map<string, NavigationState>());
  private readonly connectionState = signal<ConnectionState>("disconnected");
  private readonly requestStatusState = signal<RequestStatus | undefined>(undefined);
  private readonly errorState = signal<string | undefined>(undefined);
  private readonly frameState = signal<Blob | undefined>(undefined);
  private readonly cursorState = signal("default");
  private readonly dirtyRectangleTickState = signal(0);
  private readonly dirtyRectangleStreamState = signal<DirtyRectangleScreencastState | undefined>(
    undefined,
  );

  readonly tabs = this.tabsState.asReadonly();
  readonly connection = this.connectionState.asReadonly();
  readonly requestStatus = this.requestStatusState.asReadonly();
  readonly error = this.errorState.asReadonly();
  readonly frame = this.frameState.asReadonly();
  readonly cursor = this.cursorState.asReadonly();
  /** Bumped whenever canvas work arrived; read it to drain the queue. */
  readonly dirtyRectangleTick = this.dirtyRectangleTickState.asReadonly();
  /** Coverage and volume of the patch stream, or nothing when it is not used. */
  readonly dirtyRectangleStream = this.dirtyRectangleStreamState.asReadonly();
  readonly transportMode = this.screencastMode.mode;
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

  /** Lease a browser. Answers with the capacity left, or nothing if it failed. */
  async open(): Promise<number | undefined> {
    this.connectionState.set("connecting");
    this.errorState.set(undefined);
    const request = this.beginRequest();
    try {
      const response = await openSession(
        {
          owner_id: this.identity.ownerId,
          request_id: request.id,
          timeout_seconds: SESSION_REQUEST_TIMEOUT_SECONDS,
        },
        { signal: request.controller.signal },
      );
      if (response.status !== 201) throw new Error(openSessionError(response));
      await this.start(response.data);
      return response.data.remaining_capacity;
    } catch (error) {
      await this.abandon(error);
      return undefined;
    } finally {
      this.finishRequest(request);
    }
  }

  /**
   * Take a session this client already owns back over.
   *
   * The lease outlives the page, so a reload reconnects to the browser it was
   * looking at rather than leasing a second one. A session that was parked in
   * the meantime is resumed onto whichever browser is free now.
   */
  async attach(sessionId: string): Promise<boolean> {
    this.connectionState.set("connecting");
    this.errorState.set(undefined);
    try {
      const response = await getSession(sessionId);
      if (response.status !== 200) {
        throw new Error(`Session could not be read (${response.status})`);
      }
      await this.start(
        response.data.status === "suspended" ? await this.resume(sessionId) : response.data,
      );
      return true;
    } catch (error) {
      await this.abandon(error);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    this.connectionState.set("disconnected");
    const client = this.client;
    const screencast = this.screencast;
    const dirtyRectangles = this.dirtyRectangles;
    const session = this.sessionState();
    const request = this.pendingRequest;
    this.pendingRequest = undefined;
    this.requestStatusState.set(undefined);
    request?.controller.abort();
    this.client = undefined;
    this.transport = undefined;
    this.screencast = undefined;
    this.dirtyRectangles = undefined;
    this.sessionState.set(undefined);
    this.frameState.set(undefined);
    this.dirtyRectangleStreamState.set(undefined);
    this.enqueueDirtyRectangleEvent({ kind: "reset", generation: 0 });
    screencast?.close();
    dirtyRectangles?.close();
    await client?.close().catch(() => undefined);
    if (request) {
      await cancelSessionRequest(request.id, { owner_id: this.identity.ownerId }).catch(
        () => undefined,
      );
    }
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

  private async start(session: SessionResponse): Promise<void> {
    // An active session carries both paths; a suspended one holds no browser
    // and leaves them empty, which is nothing this can connect to.
    if (!session.tunnel_path || !session.screencast_path) {
      throw new Error("The session does not contain a browser");
    }
    this.sessionState.set(session);
    const transport = new WebSocketRpcTransport(socketUrl(session.tunnel_path));
    const client = new BackendBrowserClient(transport);
    this.transport = transport;
    this.client = client;
    await transport.connect();
    const mode = this.transportMode();
    const screencast = screencastUrl(session.screencast_path, mode);
    await (mode === "dirty-rectangles"
      ? this.connectDirtyRectangleScreencast(screencast)
      : this.connectScreencast(screencast));
    this.connectionState.set("connected");
    void this.receiveNotifications();
    this.tabsState.set((await client.browser.tab.list()).tabs);
  }

  private async resume(sessionId: string): Promise<SessionResponse> {
    const request = this.beginRequest();
    try {
      const response = await resumeSession(
        sessionId,
        {
          request_id: request.id,
          timeout_seconds: SESSION_REQUEST_TIMEOUT_SECONDS,
        },
        { signal: request.controller.signal },
      );
      if (response.status !== 200) {
        throw new Error(`Session could not be resumed (${response.status})`);
      }
      return response.data;
    } finally {
      this.finishRequest(request);
    }
  }

  private beginRequest(): PendingSessionRequest {
    const request = { id: crypto.randomUUID(), controller: new AbortController() };
    this.pendingRequest = request;
    this.requestStatusState.set(undefined);
    void this.watchRequest(request);
    return request;
  }

  private finishRequest(request: PendingSessionRequest): void {
    if (this.pendingRequest !== request) return;
    this.pendingRequest = undefined;
    this.requestStatusState.set(undefined);
    request.controller.abort();
  }

  private async watchRequest(request: PendingSessionRequest): Promise<void> {
    try {
      while (this.pendingRequest === request) {
        await delay(500);
        if (this.pendingRequest !== request) return;
        const response = await getSessionRequest(
          request.id,
          { owner_id: this.identity.ownerId },
          { signal: request.controller.signal },
        );
        if (response.status === 200) this.requestStatusState.set(response.data.status);
      }
    } catch {
      // The blocking session request remains authoritative. A missed status
      // poll should not make an otherwise healthy acquisition fail.
      return;
    }
  }

  /** Give up on a half-built connection without leaving its browser leased. */
  private async abandon(error: unknown): Promise<void> {
    await this.disconnect();
    this.reportError(error);
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

  /**
   * Subscribe to changed tiles instead of whole frames.
   *
   * The patch stream owns its own reconnects: a canvas built from patches can
   * only be repaired by subscribing again, so dropping the connection is the
   * repair rather than a failure to report. Only a stream that stays down is.
   */
  private async connectDirtyRectangleScreencast(url: URL): Promise<void> {
    const stream = new DirtyRectangleScreencast(url, {
      onReset: (generation) => this.enqueueDirtyRectangleEvent({ kind: "reset", generation }),
      onUpdate: (update) => this.enqueueDirtyRectangleEvent({ kind: "update", update }),
      onState: (state) => {
        if (stream === this.dirtyRectangles) this.dirtyRectangleStreamState.set(state);
      },
      onError: (message) => {
        if (stream === this.dirtyRectangles) this.reportError(message);
      },
    });
    this.dirtyRectangles = stream;
    await stream.connect();
  }

  /** Hand the canvas everything that arrived since it last drew. */
  takeDirtyRectangleEvents(): readonly DirtyRectangleEvent[] {
    return this.dirtyRectangleQueue.splice(0);
  }

  private enqueueDirtyRectangleEvent(event: DirtyRectangleEvent): void {
    // A reset makes everything queued behind it moot: it is the canvas being
    // thrown away, and the updates before it were painted onto that canvas.
    if (event.kind === "reset") this.dirtyRectangleQueue.length = 0;
    this.dirtyRectangleQueue.push(event);
    this.dirtyRectangleTickState.update((tick) => tick + 1);
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

/** One screencast endpoint serves every packaging; the mode picks one. */
function screencastUrl(path: string, mode: ScreencastMode): URL {
  const url = socketUrl(path);
  url.searchParams.set("mode", mode);
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
  // A queued request that ran out of time or was ended says so itself; the
  // rest are input errors this client should not have sent.
  if (response.status === 408 || response.status === 409) return response.data.message;
  return `Session could not be opened (${response.status})`;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
