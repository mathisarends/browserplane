import { Injectable } from "@angular/core";

const STORAGE_KEY = "browserplane.client-id";
const UUID_PATTERN = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i;

@Injectable({ providedIn: "root" })
export class ClientIdentity {
  readonly ownerId = readOwnerId();
}

function readOwnerId(): string {
  const created = crypto.randomUUID();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && UUID_PATTERN.test(stored)) return stored;
    localStorage.setItem(STORAGE_KEY, created);
  } catch {}
  return created;
}
