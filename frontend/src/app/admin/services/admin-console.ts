import { computed, Injectable, signal } from "@angular/core";
import {
  closeSession,
  listBrowserStateSnapshots,
  listPooledBrowsers,
  listSessions,
  releasePooledBrowser,
  restartPooledBrowser,
  resumeSession,
  suspendSession,
} from "@browsertunnel/backend-client";
import type {
  BrowserStateSnapshotResponse,
  PooledBrowserResponse,
  SessionResponse,
} from "@browsertunnel/backend-client";
import { shortId } from "./format";

/** How long a session resumed from the admin panel may hold its browser. */
const RESUME_TTL_SECONDS = 600;

export type AdminNotice = { readonly tone: "success" | "error"; readonly text: string };

/**
 * The operator's read of the backend, refreshed as a whole.
 *
 * Every action here changes something another list already shows — releasing
 * a browser ends its session — so nothing is patched in place: one refresh
 * after each call keeps the panel honest instead of merely fast.
 */
@Injectable({ providedIn: "root" })
export class AdminConsole {
  private readonly browserState = signal<readonly PooledBrowserResponse[]>([]);
  private readonly sessionState = signal<readonly SessionResponse[]>([]);
  private readonly snapshotState = signal<readonly BrowserStateSnapshotResponse[]>([]);
  private readonly loadingState = signal(false);
  private readonly busyState = signal<ReadonlySet<string>>(new Set());
  private readonly noticeState = signal<AdminNotice | undefined>(undefined);
  private readonly refreshedState = signal<Date | undefined>(undefined);

  readonly browsers = this.browserState.asReadonly();
  readonly sessions = this.sessionState.asReadonly();
  readonly snapshots = this.snapshotState.asReadonly();
  readonly loading = this.loadingState.asReadonly();
  readonly notice = this.noticeState.asReadonly();
  readonly refreshedAt = this.refreshedState.asReadonly();

  /** Whether the first read landed, so empty lists can be told from no data. */
  readonly loaded = computed(() => this.refreshedAt() !== undefined);
  readonly activeSessions = computed(() =>
    this.sessions().filter((session) => session.status === "active"),
  );
  readonly suspendedSessions = computed(() =>
    this.sessions().filter((session) => session.status === "suspended"),
  );
  readonly availableBrowsers = computed(() =>
    this.browsers().filter((browser) => browser.state === "ready"),
  );
  readonly offlineBrowsers = computed(() =>
    this.browsers().filter((browser) => browser.state === "stopped" || browser.state === "failed"),
  );

  isBusy(id: string): boolean {
    return this.busyState().has(id);
  }

  dismissNotice(): void {
    this.noticeState.set(undefined);
  }

  async refresh(): Promise<void> {
    this.loadingState.set(true);
    try {
      const [browsers, sessions, snapshots] = await Promise.all([
        listPooledBrowsers(),
        listSessions(),
        listBrowserStateSnapshots(),
      ]);
      if (browsers.status !== 200) throw new Error(`Pool unavailable (${browsers.status})`);
      if (sessions.status !== 200) throw new Error(`Sessions unavailable (${sessions.status})`);
      this.browserState.set(browsers.data);
      this.sessionState.set(sessions.data);
      if (snapshots.status === 200) this.snapshotState.set(snapshots.data);
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
      if (response.status !== 200) throw failure("Browser could not be released", response);
    });
  }

  restartBrowser(browserId: string): Promise<void> {
    return this.run(browserId, `Browser ${shortId(browserId)} restarted`, async () => {
      const response = await restartPooledBrowser(browserId);
      if (response.status !== 200) throw failure("Browser could not be restarted", response);
    });
  }

  suspendSession(sessionId: string): Promise<void> {
    return this.run(sessionId, `Session ${shortId(sessionId)} suspended`, async () => {
      const response = await suspendSession(sessionId);
      if (response.status !== 200) throw failure("Session could not be suspended", response);
    });
  }

  resumeSession(sessionId: string): Promise<void> {
    return this.run(sessionId, `Session ${shortId(sessionId)} resumed`, async () => {
      const response = await resumeSession(sessionId, { ttl_seconds: RESUME_TTL_SECONDS });
      if (response.status !== 200) throw failure("Session could not be resumed", response);
    });
  }

  closeSession(sessionId: string): Promise<void> {
    return this.run(sessionId, `Session ${shortId(sessionId)} closed`, async () => {
      const response = await closeSession(sessionId);
      if (response.status !== 204) throw failure("Session could not be closed", response);
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
    this.busyState.update((current) => {
      const next = new Set(current);
      if (busy) next.add(id);
      else next.delete(id);
      return next;
    });
  }
}

/** Prefer the backend's own explanation; fall back to the bare status. */
function failure(fallback: string, response: { status: number; data: unknown }): Error {
  const data = response.data;
  if (data && typeof data === "object" && "message" in data && typeof data.message === "string") {
    return new Error(data.message);
  }
  return new Error(`${fallback} (${response.status})`);
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : "The backend could not be reached";
}
