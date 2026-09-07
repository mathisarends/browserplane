import { signal } from "@angular/core";
import {
  DirtyRectangleScreencast,
  type DirtyRectangleEvent,
  type DirtyRectangleScreencastState,
} from "./dirty-rectangle-screencast";
import type { ScreencastMode } from "./screencast-mode";
import { screencastOpened, screencastUrl, SCREENCAST_DISCONNECTED } from "./socket";

export class ScreencastStream {
  private readonly frameState = signal<Blob | undefined>(undefined);
  private readonly tickState = signal(0);
  private readonly dirtyRectangleState = signal<DirtyRectangleScreencastState | undefined>(
    undefined,
  );
  private readonly queue: DirtyRectangleEvent[] = [];
  private frames?: WebSocket;
  private patches?: DirtyRectangleScreencast;

  readonly frame = this.frameState.asReadonly();
  readonly tick = this.tickState.asReadonly();
  readonly dirtyRectangles = this.dirtyRectangleState.asReadonly();

  constructor(private readonly onError: (message: string) => void) {}

  connect(path: string, mode: ScreencastMode): Promise<void> {
    const url = screencastUrl(path, mode);
    return mode === "dirty-rectangles" ? this.connectPatches(url) : this.connectFrames(url);
  }

  close(): void {
    const frames = this.frames;
    const patches = this.patches;
    this.frames = undefined;
    this.patches = undefined;
    this.frameState.set(undefined);
    this.dirtyRectangleState.set(undefined);
    this.enqueue({ kind: "reset", generation: 0 });
    frames?.close();
    patches?.close();
  }

  take(): readonly DirtyRectangleEvent[] {
    return this.queue.splice(0);
  }

  private async connectFrames(url: URL): Promise<void> {
    const socket = new WebSocket(url);
    this.frames = socket;
    await screencastOpened(socket);
    socket.addEventListener("message", (event) => {
      if (socket === this.frames && event.data instanceof Blob) this.frameState.set(event.data);
    });
    socket.addEventListener("close", () => {
      if (socket === this.frames) this.onError(SCREENCAST_DISCONNECTED);
    });
  }

  private async connectPatches(url: URL): Promise<void> {
    const stream = new DirtyRectangleScreencast(url, {
      onReset: (generation) => this.enqueue({ kind: "reset", generation }),
      onUpdate: (update) => this.enqueue({ kind: "update", update }),
      onState: (state) => {
        if (stream === this.patches) this.dirtyRectangleState.set(state);
      },
      onError: (message) => {
        if (stream === this.patches) this.onError(message);
      },
    });
    this.patches = stream;
    await stream.connect();
  }

  private enqueue(event: DirtyRectangleEvent): void {
    if (event.kind === "reset") this.queue.length = 0;
    this.queue.push(event);
    this.tickState.update((tick) => tick + 1);
  }
}
