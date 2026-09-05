import { Injectable, signal } from "@angular/core";
import {
  captureSessionAuthenticationState,
  captureSessionBrowserState,
  mountSessionAuthenticationState,
  mountSessionBrowserState,
} from "@browsertunnel/backend-client";
import type { AuthenticationStateSchema, BrowserStateSchema } from "@browsertunnel/backend-client";

export interface BrowserSnapshot {
  readonly id: string;
  readonly name: string;
  readonly sourceBrowser: string;
  readonly createdAt: Date;
  readonly authentication: AuthenticationStateSchema;
  readonly browser: BrowserStateSchema;
}

@Injectable({ providedIn: "root" })
export class BrowserStateVault {
  private readonly snapshotState = signal<readonly BrowserSnapshot[]>([]);
  readonly snapshots = this.snapshotState.asReadonly();

  async capture(sessionId: string, sourceBrowser: string): Promise<BrowserSnapshot> {
    const [authentication, browser] = await Promise.all([
      captureSessionAuthenticationState(sessionId),
      captureSessionBrowserState(sessionId),
    ]);
    if (authentication.status !== 200) {
      throw new Error(
        `Authentication-State konnte nicht gelesen werden (${authentication.status})`,
      );
    }
    if (browser.status !== 200) {
      throw new Error(`Browser-State konnte nicht gelesen werden (${browser.status})`);
    }

    const snapshot: BrowserSnapshot = {
      id: crypto.randomUUID(),
      name: `Snapshot ${this.snapshots().length + 1}`,
      sourceBrowser,
      createdAt: new Date(),
      authentication: authentication.data,
      browser: browser.data,
    };
    this.snapshotState.update((snapshots) => [snapshot, ...snapshots]);
    return snapshot;
  }

  async mount(sessionId: string, snapshotId: string): Promise<BrowserSnapshot> {
    const snapshot = this.snapshots().find(({ id }) => id === snapshotId);
    if (!snapshot) throw new Error("Der ausgewählte Snapshot ist nicht mehr verfügbar");

    const authentication = await mountSessionAuthenticationState(
      sessionId,
      snapshot.authentication,
    );
    if (authentication.status !== 204) {
      throw new Error(
        `Authentication-State konnte nicht gemountet werden (${authentication.status})`,
      );
    }

    const browser = await mountSessionBrowserState(sessionId, snapshot.browser);
    if (browser.status !== 204) {
      throw new Error(`Browser-State konnte nicht gemountet werden (${browser.status})`);
    }
    return snapshot;
  }
}
