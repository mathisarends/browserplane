import { Injectable } from "@angular/core";

const STORAGE_KEY = "browserplane.client-id";
const UUID_PATTERN = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i;

/**
 * Who this client is, as far as the backend is concerned.
 *
 * Sessions are leased to an owner and outlive the page that opened them, so
 * the id has to outlive it too: it is what a reloaded gallery asks the backend
 * about to find its browsers again. Storage that refuses to keep it — private
 * mode, cleared site data — only costs the next reload its sessions.
 */
@Injectable({ providedIn: "root" })
export class ClientIdentity {
  readonly ownerId = readOwnerId();
}

function readOwnerId(): string {
  const created = crypto.randomUUID();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    // Anything but a UUID is refused by the backend, so a stomped key has to
    // be replaced rather than carried around forever.
    if (stored && UUID_PATTERN.test(stored)) return stored;
    localStorage.setItem(STORAGE_KEY, created);
  } catch {
    // An id nobody can store still holds this page's sessions together.
  }
  return created;
}
