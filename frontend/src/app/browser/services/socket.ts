import type { ScreencastMode } from "./screencast-mode";

export const SCREENCAST_FAILED = "Screencast connection failed";
export const SCREENCAST_DISCONNECTED = "Screencast connection was disconnected";

export function socketUrl(path: string): URL {
  const url = new URL(path, window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url;
}

export function screencastUrl(path: string, mode: ScreencastMode): URL {
  const url = socketUrl(path);
  url.searchParams.set("mode", mode);
  return url;
}

export function screencastOpened(socket: WebSocket): Promise<void> {
  return new Promise((resolve, reject) => {
    socket.addEventListener("open", () => resolve(), { once: true });
    socket.addEventListener("error", () => reject(new Error(SCREENCAST_FAILED)), { once: true });
    socket.addEventListener("close", () => reject(new Error(SCREENCAST_DISCONNECTED)), {
      once: true,
    });
  });
}
