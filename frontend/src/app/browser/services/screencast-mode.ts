import { Injectable, signal } from "@angular/core";

export const SCREENCAST_MODES = ["jpeg", "dirty-rectangles"] as const;
export type ScreencastMode = (typeof SCREENCAST_MODES)[number];

const SCREENCAST_PARAM = "screencast";
const DEFAULT_MODE: ScreencastMode = "jpeg";

/**
 * Which screencast transport the browser panels subscribe to.
 *
 * The mode is an experiment switch, not a preference: it belongs in the URL so
 * a measurement run can be shared and reloaded as the same run. Reading it once
 * at startup is deliberate - a session picks its transport when it connects,
 * and switching mid-stream would compare two things at once.
 */
@Injectable({ providedIn: "root" })
export class ScreencastModeState {
  private readonly modeState = signal(readMode());
  readonly mode = this.modeState.asReadonly();
}

function readMode(): ScreencastMode {
  const value = new URLSearchParams(window.location.search).get(SCREENCAST_PARAM);
  return isScreencastMode(value) ? value : DEFAULT_MODE;
}

function isScreencastMode(value: string | null): value is ScreencastMode {
  return SCREENCAST_MODES.includes(value as ScreencastMode);
}
