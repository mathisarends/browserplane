import { decodeDirtyRectangleUpdate, type DirtyRectangleUpdate } from "./dirty-rectangle-protocol";
import { DirtyRectangleReconciliation } from "./dirty-rectangle-reconciliation";

export interface DirtyRectangleScreencastState {
  /** Counts the subscriptions; a change means the canvas has to start empty. */
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
  /** Reconnects taken to rebuild a canvas the patch stream could not complete. */
  readonly resyncs: number;
}

export interface DirtyRectangleScreencastHandlers {
  /** Drop the canvas: a new subscription is about to repaint it from scratch. */
  onReset(generation: number): void;
  onUpdate(update: DirtyRectangleUpdate, generation: number): void;
  onState(state: DirtyRectangleScreencastState): void;
  onError(message: string): void;
}

const RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY_MS = 250;
const RECONNECT_MAX_DELAY_MS = 4_000;
/** How many partial updates to accept before demanding a whole canvas again. */
const UPDATES_BEFORE_RESYNC = 60;

/**
 * A changed-tile screencast subscription that can rebuild its own canvas.
 *
 * The worker keeps the diff state per subscription and opens every one with a
 * packet covering the whole canvas. That is the only full frame in the stream,
 * which makes reconnecting the reconciliation primitive: when the transport
 * breaks, or when the tiles received never add up to a whole canvas, this drops
 * what it holds, subscribes again, and repaints from the full canvas that a
 * fresh subscription is guaranteed to start with.
 */
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

  /**
   * Open the first subscription. Later ones are taken without being asked.
   *
   * A first connect that fails is the caller's to handle - there is no session
   * to keep alive yet - so this stops retrying and reports the failure.
   */
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
    // A resize invalidates the canvas mid-subscription; the update that
    // reported it carries the new canvas whole, so it repaints rather than
    // patches - the consumer is told to start empty first.
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

  /**
   * Subscribe again to get a whole canvas.
   *
   * Reached when tiles keep arriving but never cover everything - a canvas that
   * grew, a packet lost with the transport that carried it. Patches alone can
   * never repair that, only a new subscription can.
   */
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

/**
 * What a canvas has to replay, in order.
 *
 * A reset has to stay in line with the updates around it: applying patches that
 * were meant for a canvas thrown away in between paints them onto the wrong
 * picture.
 */
export type DirtyRectangleEvent =
  | { readonly kind: "reset"; readonly generation: number }
  | { readonly kind: "update"; readonly update: DirtyRectangleUpdate };
