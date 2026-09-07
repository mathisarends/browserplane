import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  viewChild,
} from "@angular/core";
import type { MouseParams } from "@browsertunnel/browser-rpc-client";
import { CanvasPainter } from "../services/canvas-painter";
import {
  isClipboardShortcut,
  keyParams,
  mouseButtonOf,
  mouseParams,
  releaseMouseParams,
  type MousePoint,
} from "../services/input-events";
import { BrowserSession } from "../services/browser-session";

@Component({
  selector: "app-browser-canvas",
  template: `
    <canvas
      #canvas
      width="1600"
      height="900"
      tabindex="0"
      aria-label="Browser stream"
      [style.cursor]="cursor()"
      (mousedown)="onMouseDown($event)"
      (mousemove)="onCanvasMouseMove($event)"
      (mouseleave)="onCanvasMouseMove($event)"
      (contextmenu)="$event.preventDefault()"
      (wheel)="onWheel($event)"
      (keydown)="onKeyDown($event)"
      (keyup)="onKeyUp($event)"
    ></canvas>
  `,
  styles: `
    :host {
      display: flex;
      flex: none;
      aspect-ratio: 16 / 9;
      min-height: 0;
      width: 100%;
      overflow: hidden;
      background: #020304;
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
      min-height: 0;
      background: #020304;
      outline: none;
      object-fit: contain;
    }

    canvas:focus-visible {
      box-shadow: inset 0 0 0 2px #6797ff;
    }
  `,
  host: {
    "(window:mouseup)": "onMouseUp($event)",
    "(window:mousemove)": "onWindowMouseMove($event)",
    "(window:blur)": "releaseHeldButtons()",
    "(document:paste)": "onPaste($event)",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserCanvas implements OnDestroy {
  private readonly session = inject(BrowserSession);
  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>("canvas");
  private readonly painter = computed(() => {
    const element = this.canvas()?.nativeElement;
    return element && new CanvasPainter(element);
  });

  private readonly heldButtons = new Map<number, MouseParams["button"]>();
  private pendingMove?: MouseParams;
  private moveFrame?: number;
  private lastPoint?: MousePoint;
  private input: Promise<void> = Promise.resolve();

  protected readonly cursor = this.session.page.cursor;

  constructor() {
    effect(() => {
      const frame = this.session.stream.frame();
      const painter = this.painter();
      if (frame && painter) void this.paint(() => painter.draw(frame));
    });
    effect(() => {
      this.session.stream.tick();
      const painter = this.painter();
      if (painter) void this.paint(() => painter.replay(this.session.stream.take()));
    });
  }

  ngOnDestroy(): void {
    if (this.moveFrame !== undefined) cancelAnimationFrame(this.moveFrame);
  }

  protected onMouseDown(event: MouseEvent): void {
    event.preventDefault();
    this.canvas()?.nativeElement.focus();
    const button = mouseButtonOf(event);
    this.heldButtons.set(event.button, button);
    this.flushMove();
    this.send(mouseParams("mouseDown", this.pointOf(event), button, event));
  }

  protected onMouseUp(event: MouseEvent): void {
    const button = this.heldButtons.get(event.button);
    if (button === undefined) return;
    event.preventDefault();
    this.flushMove();
    this.send(mouseParams("mouseUp", this.pointOf(event), button, event));
    this.heldButtons.delete(event.button);
  }

  protected onCanvasMouseMove(event: MouseEvent): void {
    if (this.heldButtons.size === 0) this.scheduleMove(event);
  }

  protected onWindowMouseMove(event: MouseEvent): void {
    if (this.heldButtons.size > 0) this.scheduleMove(event);
  }

  protected releaseHeldButtons(): void {
    if (this.heldButtons.size === 0) return;
    this.flushMove();
    const point = this.lastPoint ?? { x: 0, y: 0 };
    for (const button of this.heldButtons.values()) {
      this.send(releaseMouseParams(point, button));
    }
    this.heldButtons.clear();
  }

  protected onWheel(event: WheelEvent): void {
    event.preventDefault();
    void this.session.sendScroll({
      ...this.pointOf(event),
      deltaX: event.deltaX,
      deltaY: event.deltaY,
    });
  }

  protected onPaste(event: ClipboardEvent): void {
    if (document.activeElement !== this.canvas()?.nativeElement) return;
    event.preventDefault();
    const text = event.clipboardData?.getData("text/plain");
    if (text) void this.session.paste(text);
  }

  protected onKeyDown(event: KeyboardEvent): void {
    if (isClipboardShortcut(event, "v")) return;
    event.preventDefault();
    if (isClipboardShortcut(event, "c")) {
      void this.session.copy();
      return;
    }
    void this.session.sendKey(keyParams(event, "down"));
  }

  protected onKeyUp(event: KeyboardEvent): void {
    if (isClipboardShortcut(event, "v") || isClipboardShortcut(event, "c")) return;
    event.preventDefault();
    void this.session.sendKey(keyParams(event, "up"));
  }

  private pointOf(event: MouseEvent): MousePoint {
    const canvas = this.canvas()?.nativeElement;
    if (!canvas) return { x: 0, y: 0 };
    const bounds = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * canvas.width,
      y: ((event.clientY - bounds.top) / bounds.height) * canvas.height,
    };
  }

  private scheduleMove(event: MouseEvent): void {
    const point = this.pointOf(event);
    const held = this.heldButtons.values().next().value ?? "none";
    this.lastPoint = point;
    this.pendingMove = mouseParams("mouseMove", point, held, event);
    this.moveFrame ??= requestAnimationFrame(() => this.flushMove());
  }

  private flushMove(): void {
    if (this.moveFrame !== undefined) cancelAnimationFrame(this.moveFrame);
    this.moveFrame = undefined;
    const move = this.pendingMove;
    this.pendingMove = undefined;
    if (move) this.send(move);
  }

  private send(params: MouseParams): void {
    this.input = this.input.then(() => this.session.sendMouse(params));
  }

  private async paint(work: () => Promise<void>): Promise<void> {
    try {
      await work();
    } catch (error) {
      this.session.reportError(error);
    }
  }
}
