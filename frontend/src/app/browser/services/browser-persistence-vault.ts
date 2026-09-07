import { Injectable, signal } from "@angular/core";
import {
  createAuthenticationProfile,
  createBrowserCheckpoint,
  listAuthenticationProfiles,
  listBrowserCheckpoints,
  mountSessionAuthenticationProfile,
  mountSessionBrowserCheckpoint,
  type AuthenticationProfileResponse,
  type BrowserCheckpointResponse,
} from "@browsertunnel/backend-client";
import { expectStatus } from "../../shared/api";

@Injectable({ providedIn: "root" })
export class BrowserPersistenceVault {
  private readonly checkpointState = signal<readonly BrowserCheckpointResponse[]>([]);
  private readonly profileState = signal<readonly AuthenticationProfileResponse[]>([]);

  readonly checkpoints = this.checkpointState.asReadonly();
  readonly authenticationProfiles = this.profileState.asReadonly();

  constructor() {
    void this.refresh().catch(() => undefined);
  }

  async refresh(): Promise<void> {
    const [checkpoints, profiles] = await Promise.all([
      listBrowserCheckpoints(),
      listAuthenticationProfiles(),
    ]);
    if (checkpoints.status !== 200 || profiles.status !== 200) {
      throw new Error("Saved browser state could not be loaded");
    }
    this.checkpointState.set(checkpoints.data);
    this.profileState.set(profiles.data);
  }

  async createCheckpoint(sessionId: string): Promise<BrowserCheckpointResponse> {
    const response = await createBrowserCheckpoint(sessionId, {});
    expectStatus(response, 201, "Browser checkpoint could not be saved");
    this.checkpointState.update((items) => [response.data, ...items]);
    return response.data;
  }

  async mountCheckpoint(sessionId: string, checkpointId: string): Promise<void> {
    const response = await mountSessionBrowserCheckpoint(sessionId, {
      browser_checkpoint_id: checkpointId,
    });
    expectStatus(response, 204, "Browser checkpoint could not be mounted");
  }

  async createProfile(sessionId: string): Promise<AuthenticationProfileResponse> {
    const response = await createAuthenticationProfile(sessionId, {
      name: `Authentication ${this.authenticationProfiles().length + 1}`,
    });
    expectStatus(response, 201, "Authentication profile could not be saved");
    this.profileState.update((items) => [response.data, ...items]);
    return response.data;
  }

  async mountProfile(sessionId: string, profileId: string): Promise<void> {
    const response = await mountSessionAuthenticationProfile(sessionId, {
      authentication_profile_id: profileId,
    });
    expectStatus(response, 204, "Authentication profile could not be mounted");
  }
}
