import {
  closeSession,
  getSession,
  openSession,
  resumeSession,
  sessions as sessionsApi,
  type SessionResponse,
} from "@browsertunnel/backend-client";
import { BackendBrowserClient } from "@browsertunnel/browser-rpc-client";
import type {
  KeyParams,
  MouseParams,
  ScrollParams,
} from "@browsertunnel/browser-rpc-client/models";
import { computed, signal } from "@lit-labs/signals";
import type { QueryClient } from "@tanstack/lit-query";
import { errorMessage } from "../../shared/errors";
import { BrowserPageState, pageFailure, type BrowserTabState } from "./browser-page-state";
import { ClientIdentity } from "./client-identity";
import { resolveNavigationTarget } from "./navigation-target";
import { ScreencastModeState } from "./screencast-mode";
import { ScreencastStream } from "./screencast-stream";
import { SESSION_REQUEST_TIMEOUT_SECONDS, SessionRequestTracker } from "./session-request-tracker";
import { socketUrl } from "./socket";
export type ConnectionState = "connecting" | "connected" | "disconnected";
export class BrowserSession {
  constructor(
    private readonly identity: ClientIdentity,
    private readonly screencastMode: ScreencastModeState,
    private readonly queryClient: QueryClient,
  ) {}

  private generation = 0;
  private readonly requests = new SessionRequestTracker(this.identity.ownerId);
  private readonly sessionState = signal<SessionResponse | undefined>(undefined);
  private readonly connectionState = signal<ConnectionState>("disconnected");
  private readonly errorState = signal<string | undefined>(undefined);
  private client?: BackendBrowserClient;
  readonly page = new BrowserPageState();
  readonly stream = new ScreencastStream((message) => this.errorState.set(message));
  readonly requestStatus = this.requests.status;
  readonly connection = this.connectionState;
  readonly error = this.errorState;
  readonly browserId = computed(() => this.sessionState.get()?.browser_id);
  readonly sessionId = computed(() => this.sessionState.get()?.id);
  async open(): Promise<number | undefined> {
    const generation = this.beginConnecting();
    try {
      const session = await this.requests.track(async ({ id, signal }) =>
        openSession(
          {
            owner_id: this.identity.ownerId,
            request_id: id,
            timeout_seconds: SESSION_REQUEST_TIMEOUT_SECONDS,
          },
          { signal },
        ),
      );
      if (generation !== this.generation) {
        await closeSession(session.id).catch(() => undefined);
        return undefined;
      }
      if (!(await this.start(session, generation))) return undefined;
      await this.queryClient.invalidateQueries({ queryKey: sessionsApi.sessionsKeys.all });
      return session.remaining_capacity;
    } catch (error) {
      if (generation === this.generation) await this.abandon(error);
      return undefined;
    }
  }
  async attach(sessionId: string): Promise<boolean> {
    const generation = this.beginConnecting();
    try {
      const session = await getSession(sessionId);
      if (generation !== this.generation) return false;
      return await this.start(
        session.status === "suspended" ? await this.resume(sessionId) : session,
        generation,
      );
    } catch (error) {
      if (generation === this.generation) await this.abandon(error);
      return false;
    }
  }
  async disconnect(): Promise<void> {
    this.generation++;
    this.connectionState.set("disconnected");
    const client = this.client,
      session = this.sessionState.get();
    this.client = undefined;
    this.sessionState.set(undefined);
    this.page.reset();
    this.stream.close();
    await this.requests.cancel();
    await client?.close().catch(() => undefined);
    if (session) await closeSession(session.id).catch(() => undefined);
    await this.queryClient.invalidateQueries({ queryKey: sessionsApi.sessionsKeys.all });
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
      this.page.navigation.get()?.loading ? client.browser.nav.stop() : client.browser.nav.reload(),
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
  private beginConnecting(): number {
    this.generation++;
    this.connectionState.set("connecting");
    this.errorState.set(undefined);
    return this.generation;
  }
  private async start(session: SessionResponse, generation: number): Promise<boolean> {
    if (!session.tunnel_path || !session.screencast_path)
      throw new Error("The session does not contain a browser");
    if (generation !== this.generation) return false;
    this.sessionState.set(session);
    let pending: Promise<unknown> = Promise.resolve();
    const client = await BackendBrowserClient.connect({
      url: socketUrl(session.tunnel_path).href,
      reconnect: true,
      reconnectMaxAttempts: 3,
      retryAttempts: 1,
      onStateChange: (_server, state, error) => {
        if (generation !== this.generation) return;
        if (state === "closed") {
          this.connectionState.set("disconnected");
          if (error) this.reportError(error);
        } else if (state === "connecting" || state === "reconnecting")
          this.connectionState.set("connecting");
        else if (this.client) {
          this.connectionState.set("connected");
          void this.refreshTabs();
        }
      },
      middleware: [
        {
          request(_call, next) {
            const response = pending.then(next);
            pending = response.then(
              () => undefined,
              () => undefined,
            );
            return response;
          },
        },
      ],
    });
    if (generation !== this.generation) {
      await client.close();
      return false;
    }
    this.client = client;
    await this.stream.connect(session.screencast_path, this.screencastMode.mode.get());
    if (generation !== this.generation) {
      await client.close();
      return false;
    }
    this.connectionState.set("connected");
    void this.listen(client);
    this.page.setTabs((await client.browser.tab.list()).tabs);
    return true;
  }
  private resume(sessionId: string): Promise<SessionResponse> {
    return this.requests.track(async ({ id, signal }) => {
      const response = await resumeSession(
        sessionId,
        { request_id: id, timeout_seconds: SESSION_REQUEST_TIMEOUT_SECONDS },
        { signal },
      );
      return response;
    });
  }
  private async abandon(error: unknown): Promise<void> {
    await this.disconnect();
    this.reportError(error);
  }
  private async call(action: (client: BackendBrowserClient) => Promise<void>): Promise<void> {
    const client = this.client;
    if (!client) {
      if (!this.error.get()) this.reportError("RPC connection is unavailable");
      return;
    }
    try {
      await action(client);
      if (client === this.client) this.errorState.set(undefined);
    } catch (error) {
      if (client === this.client) this.reportError(error);
    }
  }
  private callForTabs(
    action: (client: BackendBrowserClient) => Promise<{
      tabs: readonly BrowserTabState[];
    }>,
  ): Promise<void> {
    return this.call(async (client) => this.page.setTabs((await action(client)).tabs));
  }
  private async listen(client: BackendBrowserClient): Promise<void> {
    try {
      for await (const event of client.browser.event()) {
        if (client !== this.client) return;
        this.page.apply(event);
        const failure = pageFailure(event);
        if (failure) this.errorState.set(failure);
      }
    } catch (error) {
      if (client === this.client) this.reportError(error);
    }
  }
}
