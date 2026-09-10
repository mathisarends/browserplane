import { computed, inject, Injectable, signal } from "@angular/core";
import {
  closeSession,
  getSession,
  openSession,
  resumeSession,
  type openSessionResponse,
  type SessionResponse,
} from "@browsertunnel/backend-client";
import {
  BackendBrowserClient,
  WebSocketRpcTransport,
  type KeyParams,
  type MouseParams,
  type ScrollParams,
} from "@browsertunnel/browser-rpc-client";
import { expectStatus } from "../../shared/api";
import { errorMessage } from "../../shared/errors";
import { BrowserPageState, pageFailure, type BrowserTabState } from "./browser-page-state";
import { ClientIdentity } from "./client-identity";
import { resolveNavigationTarget } from "./navigation-target";
import { ScreencastModeState } from "./screencast-mode";
import { ScreencastStream } from "./screencast-stream";
import { SESSION_REQUEST_TIMEOUT_SECONDS, SessionRequestTracker } from "./session-request-tracker";
import { socketUrl } from "./socket";

export type ConnectionState = "connecting" | "connected" | "disconnected";

@Injectable()
export class BrowserSession {
  private readonly identity = inject(ClientIdentity);
  private readonly screencastMode = inject(ScreencastModeState);
  private readonly requests = new SessionRequestTracker(this.identity.ownerId);
  private readonly sessionState = signal<SessionResponse | undefined>(undefined);
  private readonly connectionState = signal<ConnectionState>("disconnected");
  private readonly errorState = signal<string | undefined>(undefined);
  private client?: BackendBrowserClient;

  readonly page = new BrowserPageState();
  readonly stream = new ScreencastStream((message) => this.errorState.set(message));
  readonly requestStatus = this.requests.status;
  readonly connection = this.connectionState.asReadonly();
  readonly error = this.errorState.asReadonly();
  readonly browserId = computed(() => this.sessionState()?.browser_id);
  readonly sessionId = computed(() => this.sessionState()?.id);

  async open(): Promise<number | undefined> {
    this.beginConnecting();
    try {
      const session = await this.requests.track(async ({ id, signal }) => {
        const response = await openSession(
          {
            owner_id: this.identity.ownerId,
            request_id: id,
            timeout_seconds: SESSION_REQUEST_TIMEOUT_SECONDS,
          },
          { signal },
        );
        if (response.status !== 201) throw new Error(openSessionFailure(response));
        return response.data;
      });
      await this.start(session);
      return session.remaining_capacity;
    } catch (error) {
      await this.abandon(error);
      return undefined;
    }
  }

  async attach(sessionId: string): Promise<boolean> {
    this.beginConnecting();
    try {
      const response = await getSession(sessionId);
      expectStatus(response, 200, "Session could not be read");
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
    const session = this.sessionState();
    this.client = undefined;
    this.sessionState.set(undefined);
    this.page.reset();
    this.stream.close();
    await this.requests.cancel();
    await client?.close().catch(() => undefined);
    if (session) await closeSession(session.id).catch(() => undefined);
  }

  navigate(value: string): Promise<void> {
    const url = resolveNavigationTarget(value);
    return this.call((client) => client.browser.nav.navigate({ url }));
  }

  back(): Promise<void> {
    return this.call((client) => client.browser.nav.back());
  }

  forward(): Promise<void> {
    return this.call((client) => client.browser.nav.forward());
  }

  reloadOrStop(): Promise<void> {
    return this.call((client) =>
      this.page.navigation()?.loading ? client.browser.nav.stop() : client.browser.nav.reload(),
    );
  }

  createTab(): Promise<void> {
    return this.callForTabs((client) => client.browser.tab.create({ url: "about:blank" }));
  }

  refreshTabs(): Promise<void> {
    return this.callForTabs((client) => client.browser.tab.list());
  }

  activateTab(tabId: string): Promise<void> {
    return this.callForTabs((client) => client.browser.tab.activate({ tabId }));
  }

  closeTab(tabId: string): Promise<void> {
    return this.callForTabs((client) => client.browser.tab.close({ tabId }));
  }

  sendMouse(params: MouseParams): Promise<void> {
    return this.call((client) => client.browser.input.mouse(params));
  }

  sendScroll(params: ScrollParams): Promise<void> {
    return this.call((client) => client.browser.input.scroll(params));
  }

  sendKey(params: KeyParams): Promise<void> {
    return this.call((client) => client.browser.input.key(params));
  }

  paste(text: string): Promise<void> {
    return this.call((client) => client.browser.input.paste({ text }));
  }

  copy(): Promise<void> {
    return this.call(async (client) => {
      const { text } = await client.browser.clipboard.copy();
      if (text) await navigator.clipboard.writeText(text);
    });
  }

  reportError(error: unknown): void {
    this.errorState.set(errorMessage(error));
  }

  private beginConnecting(): void {
    this.connectionState.set("connecting");
    this.errorState.set(undefined);
  }

  private async start(session: SessionResponse): Promise<void> {
    if (!session.tunnel_path || !session.screencast_path) {
      throw new Error("The session does not contain a browser");
    }
    this.sessionState.set(session);
    const transport = new WebSocketRpcTransport(socketUrl(session.tunnel_path));
    const client = new BackendBrowserClient(transport);
    this.client = client;
    await transport.connect();
    await this.stream.connect(session.screencast_path, this.screencastMode.mode());
    this.connectionState.set("connected");
    void this.listen(client);
    this.page.setTabs((await client.browser.tab.list()).tabs);
  }

  private resume(sessionId: string): Promise<SessionResponse> {
    return this.requests.track(async ({ id, signal }) => {
      const response = await resumeSession(
        sessionId,
        { request_id: id, timeout_seconds: SESSION_REQUEST_TIMEOUT_SECONDS },
        { signal },
      );
      expectStatus(response, 200, "Session could not be resumed");
      return response.data;
    });
  }

  private async abandon(error: unknown): Promise<void> {
    await this.disconnect();
    this.reportError(error);
  }

  private async call(action: (client: BackendBrowserClient) => Promise<void>): Promise<void> {
    if (!this.client) {
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

  private callForTabs(
    action: (client: BackendBrowserClient) => Promise<{ tabs: readonly BrowserTabState[] }>,
  ): Promise<void> {
    return this.call(async (client) => this.page.setTabs((await action(client)).tabs));
  }

  private async listen(client: BackendBrowserClient): Promise<void> {
    try {
      for await (const { params } of client.notifications()) {
        if (client !== this.client) return;
        this.page.apply(params);
        const failure = pageFailure(params);
        if (failure) this.errorState.set(failure);
      }
    } catch (error) {
      if (client === this.client) this.reportError(error);
    }
  }
}

function openSessionFailure(response: openSessionResponse): string {
  if (response.status === 408 || response.status === 409) {
    return response.data.detail ?? response.data.title;
  }
  return `Session could not be opened (${response.status})`;
}
