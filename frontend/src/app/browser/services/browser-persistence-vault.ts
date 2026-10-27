import {
  createAuthenticationProfile,
  createBrowserCheckpoint,
  mountSessionAuthenticationProfile,
  mountSessionBrowserCheckpoint,
  sessions as sessionsApi,
  type AuthenticationProfileResponse,
  type BrowserCheckpointResponse,
} from "@browsertunnel/backend-client";
import { signal } from "@lit-labs/signals";
import type { QueryClient } from "@tanstack/lit-query";
export class BrowserPersistenceVault {
  private readonly checkpointState = signal<readonly BrowserCheckpointResponse[]>([]);
  private readonly profileState = signal<readonly AuthenticationProfileResponse[]>([]);
  readonly checkpoints = this.checkpointState;
  readonly authenticationProfiles = this.profileState;
  constructor(private readonly queryClient: QueryClient) {
    void this.refresh().catch(() => undefined);
  }
  async refresh(): Promise<void> {
    const [checkpoints, profiles] = await Promise.all([
      this.queryClient.fetchQuery(sessionsApi.listBrowserCheckpointsQuery()),
      this.queryClient.fetchQuery(sessionsApi.listAuthenticationProfilesQuery()),
    ]);
    this.checkpointState.set(checkpoints);
    this.profileState.set(profiles);
  }
  async createCheckpoint(sessionId: string): Promise<BrowserCheckpointResponse> {
    const response = await createBrowserCheckpoint(sessionId, {});
    this.checkpointState.set(((items) => [response, ...items])(this.checkpointState.get()));
    await this.queryClient.invalidateQueries({ queryKey: sessionsApi.sessionsKeys.all });
    return response;
  }
  async mountCheckpoint(sessionId: string, checkpointId: string): Promise<void> {
    const response = await mountSessionBrowserCheckpoint(sessionId, {
      browser_checkpoint_id: checkpointId,
    });
  }
  async createProfile(sessionId: string): Promise<AuthenticationProfileResponse> {
    const response = await createAuthenticationProfile(sessionId, {
      name: `Authentication ${this.authenticationProfiles.get().length + 1}`,
    });
    this.profileState.set(((items) => [response, ...items])(this.profileState.get()));
    return response;
  }
  async mountProfile(sessionId: string, profileId: string): Promise<void> {
    const response = await mountSessionAuthenticationProfile(sessionId, {
      authentication_profile_id: profileId,
    });
  }
}
