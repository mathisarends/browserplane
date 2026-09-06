import type { DirtyRectangleUpdate } from "./dirty-rectangle-protocol";

export interface DirtyRectangleCoverage {
  readonly canvasWidth: number;
  readonly canvasHeight: number;
  readonly tiles: number;
  readonly coveredTiles: number;
  /** Every tile of the canvas has been painted at least once since the reset. */
  readonly complete: boolean;
}

export interface DirtyRectangleReconciliationResult extends DirtyRectangleCoverage {
  /** The canvas changed size, so whatever was painted before is worthless. */
  readonly resized: boolean;
}

const EMPTY_COVERAGE: DirtyRectangleCoverage = {
  canvasWidth: 0,
  canvasHeight: 0,
  tiles: 0,
  coveredTiles: 0,
  complete: false,
};

/**
 * Tracks how much of the canvas a patch stream has actually painted.
 *
 * A dirty rectangle stream only ever describes what changed, so a client that
 * joins late, drops a packet, or loses its canvas holds a picture it cannot
 * tell apart from a correct one. This keeps that judgement explicit: it starts
 * from nothing on every reset, marks the tiles each update paints, and reports
 * whether the canvas is whole. Until it is, the caller has to ask the worker
 * for a full canvas rather than trust what is on screen.
 *
 * The tile grid is learned from the patches themselves - the worker sends its
 * tile size only implicitly, and the widest patch seen is that tile size, since
 * only the last column and row are clipped to the canvas.
 */
export class DirtyRectangleReconciliation {
  private tileWidth = 0;
  private tileHeight = 0;
  private columns = 0;
  private rows = 0;
  private canvasWidth = 0;
  private canvasHeight = 0;
  private covered = new Uint8Array(0);
  private coveredCount = 0;

  get coverage(): DirtyRectangleCoverage {
    if (this.tiles === 0) return EMPTY_COVERAGE;
    return {
      canvasWidth: this.canvasWidth,
      canvasHeight: this.canvasHeight,
      tiles: this.tiles,
      coveredTiles: this.coveredCount,
      complete: this.coveredCount === this.tiles,
    };
  }

  /** Forget the painted canvas — used whenever the transport was interrupted. */
  reset(): void {
    this.tileWidth = 0;
    this.tileHeight = 0;
    this.columns = 0;
    this.rows = 0;
    this.canvasWidth = 0;
    this.canvasHeight = 0;
    this.covered = new Uint8Array(0);
    this.coveredCount = 0;
  }

  apply(update: DirtyRectangleUpdate): DirtyRectangleReconciliationResult {
    const resized =
      update.canvasWidth !== this.canvasWidth || update.canvasHeight !== this.canvasHeight;
    if (resized) {
      this.reset();
      this.canvasWidth = update.canvasWidth;
      this.canvasHeight = update.canvasHeight;
    }

    const tileWidth = Math.max(this.tileWidth, ...update.patches.map((patch) => patch.width));
    const tileHeight = Math.max(this.tileHeight, ...update.patches.map((patch) => patch.height));
    if (tileWidth !== this.tileWidth || tileHeight !== this.tileHeight) {
      this.regrid(tileWidth, tileHeight);
    }

    for (const patch of update.patches) {
      const column = Math.floor(patch.x / this.tileWidth);
      const row = Math.floor(patch.y / this.tileHeight);
      if (column >= this.columns || row >= this.rows) continue;
      const index = row * this.columns + column;
      if (this.covered[index]) continue;
      this.covered[index] = 1;
      this.coveredCount += 1;
    }

    return { ...this.coverage, resized };
  }

  private get tiles(): number {
    return this.columns * this.rows;
  }

  /**
   * Adopt a larger tile size than the one seen so far.
   *
   * Only an edge patch is smaller than a tile, so a wider patch means the grid
   * was guessed from one. The tiles counted under the old guess cannot be
   * mapped onto the new grid, so coverage starts over rather than claiming
   * pixels it no longer knows about.
   */
  private regrid(tileWidth: number, tileHeight: number): void {
    this.tileWidth = Math.max(tileWidth, 1);
    this.tileHeight = Math.max(tileHeight, 1);
    this.columns = Math.ceil(this.canvasWidth / this.tileWidth);
    this.rows = Math.ceil(this.canvasHeight / this.tileHeight);
    this.covered = new Uint8Array(this.columns * this.rows);
    this.coveredCount = 0;
  }
}
