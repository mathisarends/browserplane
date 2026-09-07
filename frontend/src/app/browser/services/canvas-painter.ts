import type { DirtyRectangleUpdate } from "./dirty-rectangle-protocol";
import type { DirtyRectangleEvent } from "./dirty-rectangle-screencast";

const CANVAS_BACKGROUND = "#020304";

export class CanvasPainter {
  private latestFrame?: Blob;
  private drawing = false;
  private readonly events: DirtyRectangleEvent[] = [];
  private replaying = false;

  constructor(private readonly canvas: HTMLCanvasElement) {}

  async draw(frame: Blob): Promise<void> {
    this.latestFrame = frame;
    if (this.drawing) return;
    this.drawing = true;
    try {
      while (this.latestFrame) {
        const pending = this.latestFrame;
        this.latestFrame = undefined;
        await this.paint(pending);
      }
    } finally {
      this.drawing = false;
    }
  }

  async replay(events: readonly DirtyRectangleEvent[]): Promise<void> {
    this.events.push(...events);
    if (this.replaying) return;
    this.replaying = true;
    try {
      for (let event = this.events.shift(); event; event = this.events.shift()) {
        if (event.kind === "reset") this.clear();
        else await this.patch(event.update);
      }
    } finally {
      this.replaying = false;
    }
  }

  private async paint(frame: Blob): Promise<void> {
    const bitmap = await createImageBitmap(frame);
    this.resize(bitmap.width, bitmap.height);
    this.context()?.drawImage(bitmap, 0, 0);
    bitmap.close();
  }

  private async patch(update: DirtyRectangleUpdate): Promise<void> {
    this.resize(update.canvasWidth, update.canvasHeight);
    const context = this.context();
    if (!context) return;
    const bitmaps = await Promise.all(update.patches.map((patch) => createImageBitmap(patch.jpeg)));
    bitmaps.forEach((bitmap, index) => {
      const patch = update.patches[index];
      context.drawImage(bitmap, patch.x, patch.y);
      bitmap.close();
    });
  }

  private clear(): void {
    const context = this.context();
    if (!context) return;
    context.fillStyle = CANVAS_BACKGROUND;
    context.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  private resize(width: number, height: number): void {
    if (this.canvas.width === width && this.canvas.height === height) return;
    this.canvas.width = width;
    this.canvas.height = height;
  }

  private context(): CanvasRenderingContext2D | null {
    return this.canvas.getContext("2d");
  }
}
