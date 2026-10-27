import { signal } from "@lit-labs/signals";
export const SCREENCAST_MODES = ["jpeg", "dirty-rectangles"] as const;
export type ScreencastMode = (typeof SCREENCAST_MODES)[number];
const SCREENCAST_PARAM = "screencast";
const DEFAULT_MODE: ScreencastMode = "dirty-rectangles";
export class ScreencastModeState {
  private readonly modeState = signal(readMode());
  readonly mode = this.modeState;
}
function readMode(): ScreencastMode {
  const value = new URLSearchParams(window.location.search).get(SCREENCAST_PARAM);
  return isScreencastMode(value) ? value : DEFAULT_MODE;
}
function isScreencastMode(value: string | null): value is ScreencastMode {
  return SCREENCAST_MODES.includes(value as ScreencastMode);
}
