import { Injectable, signal } from "@angular/core";
import {
  captureBrowserStateSnapshot,
  listBrowserStateSnapshots,
  mountSessionAuthenticationState,
  mountSessionBrowserState,
} from "@browsertunnel/backend-client";
import type { BrowserStateSnapshotResponse } from "@browsertunnel/backend-client";

@Injectable({ providedIn: "root" })
export class BrowserStateVault {
  private readonly snapshotState = signal<readonly BrowserStateSnapshotResponse[]>([]);
  readonly snapshots = this.snapshotState.asReadonly();

  constructor() {
    void this.refresh().catch(() => undefined);
  }

  async refresh(): Promise<void> {
    const response = await listBrowserStateSnapshots();
    if (response.status !== 200) {
      throw new Error(
        `Gespeicherte Browser-States konnten nicht geladen werden (${response.status})`,
      );
    }
    this.snapshotState.set(response.data);
  }

  async capture(sessionId: string, sourceBrowser: string): Promise<BrowserStateSnapshotResponse> {
    await this.refresh();
    const response = await captureBrowserStateSnapshot(sessionId, {
      name: `Snapshot ${this.snapshots().length + 1}`,
      source_browser: sourceBrowser,
    });
    if (response.status !== 201) {
      throw new Error(`Browserzustand konnte nicht gespeichert werden (${response.status})`);
    }

    const snapshot = response.data;
    this.snapshotState.update((snapshots) => [snapshot, ...snapshots]);
    return snapshot;
  }

  async mount(sessionId: string, snapshotId: string): Promise<BrowserStateSnapshotResponse> {
    const snapshot = this.snapshots().find(({ id }) => id === snapshotId);
    if (!snapshot) throw new Error("Der ausgewählte Snapshot ist nicht mehr verfügbar");

    const authentication = await mountSessionAuthenticationState(
      sessionId,
      snapshot.authentication_state,
    );
    if (authentication.status !== 204) {
      throw new Error(
        `Authentication-State konnte nicht gemountet werden (${authentication.status})`,
      );
    }

    const browser = await mountSessionBrowserState(sessionId, snapshot.browser_state);
    if (browser.status !== 204) {
      throw new Error(`Browser-State konnte nicht gemountet werden (${browser.status})`);
    }
    return snapshot;
  }
}
