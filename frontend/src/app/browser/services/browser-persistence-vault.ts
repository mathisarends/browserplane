import { Injectable, signal } from "@angular/core";
import {
  createAuthenticationProfile,
  createBrowserCheckpoint,
  deleteAuthenticationProfile,
  listAuthenticationProfiles,
  listBrowserCheckpoints,
  mountSessionAuthenticationProfile,
  mountSessionBrowserCheckpoint,
  updateAuthenticationProfile,
} from "@browsertunnel/backend-client";
import type {
  AuthenticationProfileResponse,
  BrowserCheckpointResponse,
} from "@browsertunnel/backend-client";

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
    if (response.status !== 201) {
      throw new Error(`Browser checkpoint could not be saved (${response.status})`);
    }
    this.checkpointState.update((items) => [response.data, ...items]);
    return response.data;
  }

  async mountCheckpoint(
    sessionId: string,
    checkpointId: string,
  ): Promise<BrowserCheckpointResponse> {
    const checkpoint = this.checkpoints().find(({ id }) => id === checkpointId);
    if (!checkpoint) throw new Error("The selected browser checkpoint is unavailable");
    const response = await mountSessionBrowserCheckpoint(sessionId, {
      browser_checkpoint_id: checkpointId,
    });
    if (response.status !== 204) {
      throw new Error(`Browser checkpoint could not be mounted (${response.status})`);
    }
    return checkpoint;
  }

  async createProfile(sessionId: string): Promise<AuthenticationProfileResponse> {
    const response = await createAuthenticationProfile(sessionId, {
      name: `Authentication ${this.authenticationProfiles().length + 1}`,
    });
    if (response.status !== 201) {
      throw new Error(`Authentication profile could not be saved (${response.status})`);
    }
    this.profileState.update((items) => [response.data, ...items]);
    return response.data;
  }

  async mountProfile(sessionId: string, profileId: string): Promise<AuthenticationProfileResponse> {
    const profile = this.authenticationProfiles().find(({ id }) => id === profileId);
    if (!profile) throw new Error("The selected authentication profile is unavailable");
    const response = await mountSessionAuthenticationProfile(sessionId, {
      authentication_profile_id: profileId,
    });
    if (response.status !== 204) {
      throw new Error(`Authentication profile could not be mounted (${response.status})`);
    }
    return profile;
  }

  async updateProfile(
    sessionId: string,
    profileId: string,
    name: string,
  ): Promise<AuthenticationProfileResponse> {
    const response = await updateAuthenticationProfile(sessionId, profileId, { name });
    if (response.status !== 200) {
      throw new Error(`Authentication profile could not be updated (${response.status})`);
    }
    this.profileState.update((items) =>
      items.map((item) => (item.id === profileId ? response.data : item)),
    );
    return response.data;
  }

  async deleteProfile(profileId: string): Promise<void> {
    const response = await deleteAuthenticationProfile(profileId);
    if (response.status !== 204) {
      throw new Error(`Authentication profile could not be deleted (${response.status})`);
    }
    this.profileState.update((items) => items.filter(({ id }) => id !== profileId));
  }
}
