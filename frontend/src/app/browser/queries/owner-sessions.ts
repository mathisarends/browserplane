import { sessions } from "@browsertunnel/backend-client";

export const ownerSessionsQuery = (ownerId: string) => ({
  ...sessions.listOwnerSessionsQuery({ owner_id: ownerId }),
  staleTime: 5_000,
});
