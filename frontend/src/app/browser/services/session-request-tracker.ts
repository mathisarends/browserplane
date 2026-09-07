import { signal } from "@angular/core";
import {
  cancelSessionRequest,
  getSessionRequest,
  type RequestStatus,
} from "@browsertunnel/backend-client";

export const SESSION_REQUEST_TIMEOUT_SECONDS = 60;
const POLL_INTERVAL_MS = 500;

export interface SessionRequest {
  readonly id: string;
  readonly signal: AbortSignal;
}

interface PendingRequest {
  readonly id: string;
  readonly controller: AbortController;
}

export class SessionRequestTracker {
  private readonly statusState = signal<RequestStatus | undefined>(undefined);
  private pending?: PendingRequest;

  readonly status = this.statusState.asReadonly();

  constructor(private readonly ownerId: string) {}

  async track<T>(request: (handle: SessionRequest) => Promise<T>): Promise<T> {
    const pending: PendingRequest = { id: crypto.randomUUID(), controller: new AbortController() };
    this.pending = pending;
    this.statusState.set(undefined);
    void this.poll(pending);
    try {
      const result = await request({ id: pending.id, signal: pending.controller.signal });
      this.settle(pending);
      return result;
    } catch (error) {
      await this.withdraw(pending);
      throw error;
    }
  }

  cancel(): Promise<void> {
    return this.withdraw(this.pending);
  }

  private async withdraw(pending: PendingRequest | undefined): Promise<void> {
    if (!pending) return;
    const wasPending = this.pending === pending;
    this.settle(pending);
    if (wasPending) {
      await cancelSessionRequest(pending.id, { owner_id: this.ownerId }).catch(() => undefined);
    }
  }

  private settle(pending: PendingRequest): void {
    if (this.pending !== pending) return;
    this.pending = undefined;
    this.statusState.set(undefined);
    pending.controller.abort();
  }

  private async poll(pending: PendingRequest): Promise<void> {
    try {
      while (this.pending === pending) {
        await delay(POLL_INTERVAL_MS);
        if (this.pending !== pending) return;
        const response = await getSessionRequest(
          pending.id,
          { owner_id: this.ownerId },
          { signal: pending.controller.signal },
        );
        if (response.status === 200) this.statusState.set(response.data.status);
      }
    } catch {}
  }
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
