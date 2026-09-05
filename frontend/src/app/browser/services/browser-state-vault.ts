import { Injectable, signal } from "@angular/core";
import {
  captureAuthenticationStateSnapshot,
  captureBrowserStateSnapshot,
  listAuthenticationStateSnapshots,
  listBrowserStateSnapshots,
  mountSessionAuthenticationState,
  mountSessionBrowserState,
} from "@browsertunnel/backend-client";
import type {
  AuthenticationStateSnapshotResponse,
  BrowserStateSnapshotResponse,
} from "@browsertunnel/backend-client";

@Injectable({ providedIn: "root" })
export class BrowserStateVault {
  private readonly browserSnapshotState = signal<readonly BrowserStateSnapshotResponse[]>([]);
  private readonly authenticationSnapshotState = signal<
    readonly AuthenticationStateSnapshotResponse[]
  >([]);
  readonly browserSnapshots = this.browserSnapshotState.asReadonly();
  readonly authenticationSnapshots = this.authenticationSnapshotState.asReadonly();

  constructor() {
    void this.refresh().catch(() => undefined);
  }

  async refresh(): Promise<void> {
    const [browser, authentication] = await Promise.all([
      listBrowserStateSnapshots(),
      listAuthenticationStateSnapshots(),
    ]);
    if (browser.status !== 200 || authentication.status !== 200) {
      throw new Error("Saved states could not be loaded");
    }
    this.browserSnapshotState.set(browser.data);
    this.authenticationSnapshotState.set(authentication.data);
  }

  async captureBrowser(
    sessionId: string,
    sourceBrowser: string,
  ): Promise<BrowserStateSnapshotResponse> {
    const response = await captureBrowserStateSnapshot(sessionId, {
      name: `Browser state ${this.browserSnapshots().length + 1}`,
      source_browser: sourceBrowser,
    });
    if (response.status !== 201) {
      throw new Error(`Browser state could not be saved (${response.status})`);
    }

    const snapshot = response.data;
    this.browserSnapshotState.update((snapshots) => [snapshot, ...snapshots]);
    return snapshot;
  }

  async mountBrowser(sessionId: string, snapshotId: string): Promise<BrowserStateSnapshotResponse> {
    const snapshot = this.browserSnapshots().find(({ id }) => id === snapshotId);
    if (!snapshot) throw new Error("The selected browser state is no longer available");
    const browser = await mountSessionBrowserState(sessionId, snapshot.browser_state);
    if (browser.status !== 204) {
      throw new Error(`Browser state could not be mounted (${browser.status})`);
    }
    return snapshot;
  }

  async captureAuthentication(
    sessionId: string,
    sourceBrowser: string,
  ): Promise<AuthenticationStateSnapshotResponse> {
    const response = await captureAuthenticationStateSnapshot(sessionId, {
      name: `Authentication ${this.authenticationSnapshots().length + 1}`,
      source_browser: sourceBrowser,
    });
    if (response.status !== 201) {
      throw new Error(`Authentication state could not be saved (${response.status})`);
    }
    const snapshot = response.data;
    this.authenticationSnapshotState.update((snapshots) => [snapshot, ...snapshots]);
    return snapshot;
  }

  async mountAuthentication(
    sessionId: string,
    snapshotId: string,
  ): Promise<AuthenticationStateSnapshotResponse> {
    const snapshot = this.authenticationSnapshots().find(({ id }) => id === snapshotId);
    if (!snapshot) throw new Error("The selected authentication state is no longer available");
    const response = await mountSessionAuthenticationState(
      sessionId,
      snapshot.authentication_state,
    );
    if (response.status !== 204) {
      throw new Error(`Authentication state could not be mounted (${response.status})`);
    }
    return snapshot;
  }
}
