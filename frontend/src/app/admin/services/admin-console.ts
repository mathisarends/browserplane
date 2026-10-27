import type {
  BrowserCheckpointResponse,
  PooledBrowserResponse,
  SessionResponse,
} from "@browsertunnel/backend-client";
import {
  admin as adminApi,
  closeSession,
  releasePooledBrowser,
  restartPooledBrowser,
  resumeSession,
  sessions as sessionsApi,
  suspendSession,
} from "@browsertunnel/backend-client";
import { computed, signal } from "@lit-labs/signals";
import type { QueryClient } from "@tanstack/lit-query";
import { shortId } from "./format";
const RESUME_REQUEST_TIMEOUT_SECONDS = 60;
export type AdminNotice = {
  readonly tone: "success" | "error";
  readonly text: string;
};
export class AdminConsole {
  constructor(private readonly queryClient: QueryClient) {}
  private readonly browserState = signal<readonly PooledBrowserResponse[]>([]);
  private readonly sessionState = signal<readonly SessionResponse[]>([]);
  private readonly checkpointState = signal<readonly BrowserCheckpointResponse[]>([]);
  private readonly loadingState = signal(false);
  private readonly busyState = signal<ReadonlySet<string>>(new Set());
  private readonly noticeState = signal<AdminNotice | undefined>(undefined);
  private readonly refreshedState = signal<Date | undefined>(undefined);
  readonly browsers = this.browserState;
  readonly sessions = this.sessionState;
  readonly checkpoints = this.checkpointState;
  readonly loading = this.loadingState;
  readonly notice = this.noticeState;
  readonly refreshedAt = this.refreshedState;
  readonly loaded = computed(() => this.refreshedAt.get() !== undefined);
  readonly activeSessions = computed(() =>
    this.sessions.get().filter((session) => session.status === "active"),
  );
  readonly suspendedSessions = computed(() =>
    this.sessions.get().filter((session) => session.status === "suspended"),
  );
  readonly availableBrowsers = computed(() =>
    this.browsers.get().filter((browser) => browser.state === "ready"),
  );
  readonly offlineBrowsers = computed(() =>
    this.browsers
      .get()
      .filter((browser) => browser.state === "stopped" || browser.state === "failed"),
  );
  isBusy(id: string): boolean {
    return this.busyState.get().has(id);
  }
  dismissNotice(): void {
    this.noticeState.set(undefined);
  }
  async refresh(): Promise<void> {
    this.loadingState.set(true);
    try {
      const [browsers, sessions, checkpoints] = await Promise.all([
        this.queryClient.fetchQuery(adminApi.listPooledBrowsersQuery()),
        this.queryClient.fetchQuery(adminApi.listSessionsQuery()),
        this.queryClient.fetchQuery(sessionsApi.listBrowserCheckpointsQuery()),
      ]);
      this.browserState.set(browsers);
      this.sessionState.set(sessions);
      this.checkpointState.set(checkpoints);
      this.refreshedState.set(new Date());
    } catch (error) {
      this.noticeState.set({ tone: "error", text: message(error) });
    } finally {
      this.loadingState.set(false);
    }
  }
  releaseBrowser(browserId: string): Promise<void> {
    return this.run(browserId, `Browser ${shortId(browserId)} released`, async () => {
      const response = await releasePooledBrowser(browserId);
    });
  }
  restartBrowser(browserId: string): Promise<void> {
    return this.run(browserId, `Browser ${shortId(browserId)} restarted`, async () => {
      const response = await restartPooledBrowser(browserId);
    });
  }
  suspendSession(sessionId: string): Promise<void> {
    return this.run(sessionId, `Session ${shortId(sessionId)} suspended`, async () => {
      const response = await suspendSession(sessionId);
    });
  }
  resumeSession(sessionId: string): Promise<void> {
    return this.run(sessionId, `Session ${shortId(sessionId)} resumed`, async () => {
      const response = await resumeSession(sessionId, {
        request_id: crypto.randomUUID(),
        timeout_seconds: RESUME_REQUEST_TIMEOUT_SECONDS,
      });
    });
  }
  closeSession(sessionId: string): Promise<void> {
    return this.run(sessionId, `Session ${shortId(sessionId)} closed`, async () => {
      const response = await closeSession(sessionId);
    });
  }
  private async run(id: string, success: string, action: () => Promise<void>): Promise<void> {
    if (this.isBusy(id)) return;
    this.mark(id, true);
    this.noticeState.set(undefined);
    try {
      await action();
      this.noticeState.set({ tone: "success", text: success });
    } catch (error) {
      this.noticeState.set({ tone: "error", text: message(error) });
    } finally {
      this.mark(id, false);
      await this.refresh();
    }
  }
  private mark(id: string, busy: boolean): void {
    this.busyState.set(
      ((current) => {
        const next = new Set(current);
        if (busy) next.add(id);
        else next.delete(id);
        return next;
      })(this.busyState.get()),
    );
  }
}
function message(error: unknown): string {
  return error instanceof Error ? error.message : "The backend could not be reached";
}
