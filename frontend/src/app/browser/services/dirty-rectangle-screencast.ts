import { decodeDirtyRectangleUpdate, type DirtyRectangleUpdate } from "./dirty-rectangle-protocol";
import { DirtyRectangleReconciliation } from "./dirty-rectangle-reconciliation";

export interface DirtyRectangleScreencastState {
  readonly generation: number;
  readonly connected: boolean;
  readonly complete: boolean;
  readonly canvasWidth: number;
  readonly canvasHeight: number;
  readonly tiles: number;
  readonly coveredTiles: number;
  readonly packets: number;
  readonly patches: number;
  readonly bytes: number;
  readonly resyncs: number;
}

export interface DirtyRectangleScreencastHandlers {
  onReset(generation: number): void;
  onUpdate(update: DirtyRectangleUpdate, generation: number): void;
  onState(state: DirtyRectangleScreencastState): void;
  onError(message: string): void;
}

const RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY_MS = 250;
const RECONNECT_MAX_DELAY_MS = 4_000;
const UPDATES_BEFORE_RESYNC = 60;

export class DirtyRectangleScreencast {
  private readonly reconciliation = new DirtyRectangleReconciliation();
  private socket?: WebSocket;
  private closed = false;
  private generation = 0;
  private attempt = 0;
  private updatesSinceReset = 0;
  private reconnectTimer?: number;
  private state: DirtyRectangleScreencastState = {
    generation: 0,
    connected: false,
    complete: false,
    canvasWidth: 0,
    canvasHeight: 0,
    tiles: 0,
    coveredTiles: 0,
    packets: 0,
    patches: 0,
    bytes: 0,
    resyncs: 0,
  };

  constructor(
    private readonly url: URL,
    private readonly handlers: DirtyRectangleScreencastHandlers,
  ) {}

  async connect(): Promise<void> {
    const socket = this.open();
    try {
      await new Promise<void>((resolve, reject) => {
        socket.addEventListener("open", () => resolve(), { once: true });
        socket.addEventListener("error", () => reject(new Error("Screencast connection failed")), {
          once: true,
        });
        socket.addEventListener(
          "close",
          () => reject(new Error("Screencast connection was disconnected")),
          { once: true },
        );
      });
    } catch (error) {
      this.close();
      throw error;
    }
  }

  close(): void {
    this.closed = true;
    if (this.reconnectTimer !== undefined) window.clearTimeout(this.reconnectTimer);
    this.reconnectTimer = undefined;
    const socket = this.socket;
    this.socket = undefined;
    socket?.close();
  }

  private open(): WebSocket {
    this.generation += 1;
    this.updatesSinceReset = 0;
    this.reconciliation.reset();
    this.handlers.onReset(this.generation);
    this.publish({ generation: this.generation, connected: false, ...emptyCoverage() });

    const socket = new WebSocket(this.url);
    socket.binaryType = "arraybuffer";
    this.socket = socket;
    socket.addEventListener("open", () => {
      if (socket !== this.socket) return;
      this.attempt = 0;
      this.publish({ connected: true });
    });
    socket.addEventListener("message", (event) => {
      if (socket === this.socket) this.receive(event.data);
    });
    socket.addEventListener("close", () => {
      if (socket === this.socket) this.reconnect();
    });
    return socket;
  }

  private receive(data: unknown): void {
    if (!(data instanceof ArrayBuffer)) return;
    let update: DirtyRectangleUpdate;
    try {
      update = decodeDirtyRectangleUpdate(data);
    } catch (error) {
      this.handlers.onError(error instanceof Error ? error.message : String(error));
      return;
    }

    const coverage = this.reconciliation.apply(update);
    if (coverage.resized && this.updatesSinceReset > 0) {
      this.handlers.onReset(this.generation);
    }
    this.updatesSinceReset += 1;
    this.handlers.onUpdate(update, this.generation);
    this.publish({
      connected: true,
      complete: coverage.complete,
      canvasWidth: coverage.canvasWidth,
      canvasHeight: coverage.canvasHeight,
      tiles: coverage.tiles,
      coveredTiles: coverage.coveredTiles,
      packets: this.state.packets + 1,
      patches: this.state.patches + update.patches.length,
      bytes: this.state.bytes + update.bytes,
    });

    if (!coverage.complete && this.updatesSinceReset >= UPDATES_BEFORE_RESYNC) {
      this.resync();
    }
  }

  private resync(): void {
    this.publish({ resyncs: this.state.resyncs + 1 });
    const socket = this.socket;
    this.socket = undefined;
    socket?.close();
    this.attempt = 0;
    this.open();
  }

  private reconnect(): void {
    this.socket = undefined;
    this.publish({ connected: false });
    if (this.closed) return;
    this.attempt += 1;
    if (this.attempt > RECONNECT_ATTEMPTS) {
      this.handlers.onError("Screencast connection was disconnected");
      return;
    }
    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * 2 ** (this.attempt - 1),
      RECONNECT_MAX_DELAY_MS,
    );
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = undefined;
      if (!this.closed) this.open();
    }, delay);
  }

  private publish(changes: Partial<DirtyRectangleScreencastState>): void {
    this.state = { ...this.state, ...changes };
    this.handlers.onState(this.state);
  }
}

function emptyCoverage() {
  return {
    complete: false,
    canvasWidth: 0,
    canvasHeight: 0,
    tiles: 0,
    coveredTiles: 0,
  };
}

export type DirtyRectangleEvent =
  | { readonly kind: "reset"; readonly generation: number }
  | { readonly kind: "update"; readonly update: DirtyRectangleUpdate };
