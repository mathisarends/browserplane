import {
  ChangeDetectionStrategy,
  Component,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  viewChild,
} from "@angular/core";
import type { MouseParams } from "@browsertunnel/browser-rpc-client";
import { BrowserSession } from "../services/browser-session";
import type { DirtyRectangleUpdate } from "../services/dirty-rectangle-protocol";
import type { DirtyRectangleEvent } from "../services/dirty-rectangle-screencast";

type MousePoint = Pick<MouseParams, "x" | "y">;
const MOUSE_BUTTONS = ["left", "middle", "right", "back", "forward"] as const;

@Component({
  selector: "app-browser-canvas",
  template: `
    <canvas
      #canvas
      width="1600"
      height="900"
      tabindex="0"
      aria-label="Browser stream"
      [style.cursor]="session.cursor()"
      (mousedown)="onMouseDown($event)"
      (mousemove)="onCanvasMouseMove($event)"
      (mouseleave)="onCanvasMouseMove($event)"
      (contextmenu)="preventContextMenu($event)"
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
    "(window:blur)": "releaseButtons()",
    "(document:paste)": "onPaste($event)",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserCanvas implements OnDestroy {
  protected readonly session = inject(BrowserSession);
  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>("canvas");
  private latestFrame?: Blob;
  private rendering = false;
  private readonly pendingCanvasEvents: DirtyRectangleEvent[] = [];
  private patching = false;
  private latestMove?: MouseParams;
  private animationFrame?: number;
  private inputQueue: Promise<void> = Promise.resolve();
  private lastPoint?: MousePoint;
  private readonly pressedButtons = new Map<number, MouseParams["button"]>();

  constructor() {
    effect(() => {
      const canvas = this.canvas()?.nativeElement;
      const frame = this.session.frame();
      if (!canvas || !frame) return;
      this.latestFrame = frame;
      void this.renderLatestFrame(canvas);
    });
    effect(() => {
      // Read the tick first: it is the dependency, even when there is no
      // canvas yet to draw on and the work stays queued in the session.
      this.session.dirtyRectangleTick();
      const canvas = this.canvas()?.nativeElement;
      if (!canvas) return;
      this.pendingCanvasEvents.push(...this.session.takeDirtyRectangleEvents());
      void this.applyCanvasEvents(canvas);
    });
  }

  ngOnDestroy(): void {
    if (this.animationFrame !== undefined) cancelAnimationFrame(this.animationFrame);
  }

  protected onMouseDown(event: MouseEvent): void {
    event.preventDefault();
    this.canvas()?.nativeElement.focus();
    const button = mouseButton(event.button);
    this.pressedButtons.set(event.button, button);
    this.flushMove();
    this.enqueueMouse({
      type: "mouseDown",
      ...this.point(event),
      button,
      buttons: event.buttons,
      modifiers: modifiers(event),
      clickCount: event.detail,
    });
  }

  protected onMouseUp(event: MouseEvent): void {
    const button = this.pressedButtons.get(event.button);
    if (button === undefined) return;
    event.preventDefault();
    this.flushMove();
    this.enqueueMouse({
      type: "mouseUp",
      ...this.point(event),
      button,
      buttons: event.buttons,
      modifiers: modifiers(event),
      clickCount: event.detail,
    });
    this.pressedButtons.delete(event.button);
  }

  protected onCanvasMouseMove(event: MouseEvent): void {
    if (this.pressedButtons.size === 0) this.forwardMove(event);
  }

  protected onWindowMouseMove(event: MouseEvent): void {
    if (this.pressedButtons.size > 0) this.forwardMove(event);
  }

  protected releaseButtons(): void {
    if (this.pressedButtons.size === 0) return;
    this.flushMove();
    const point = this.lastPoint ?? { x: 0, y: 0 };
    for (const button of this.pressedButtons.values()) {
      this.enqueueMouse({
        type: "mouseUp",
        ...point,
        button,
        buttons: 0,
        clickCount: 0,
      });
    }
    this.pressedButtons.clear();
  }

  protected preventContextMenu(event: Event): void {
    event.preventDefault();
  }

  protected onWheel(event: WheelEvent): void {
    event.preventDefault();
    void this.session.sendScroll({
      ...this.point(event),
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
    if (isShortcut(event, "v")) return;
    if (isShortcut(event, "c")) {
      event.preventDefault();
      void this.session.copy();
      return;
    }
    event.preventDefault();
    this.sendKey(event, keyText(event) === undefined ? "rawKeyDown" : "keyDown");
  }

  protected onKeyUp(event: KeyboardEvent): void {
    if (isShortcut(event, "v") || isShortcut(event, "c")) return;
    event.preventDefault();
    this.sendKey(event, "keyUp");
  }

  private point(event: MouseEvent | WheelEvent): MousePoint {
    const canvas = this.canvas()?.nativeElement;
    if (!canvas) return { x: 0, y: 0 };
    const bounds = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * canvas.width,
      y: ((event.clientY - bounds.top) / bounds.height) * canvas.height,
    };
  }

  private forwardMove(event: MouseEvent): void {
    const move: MouseParams = {
      type: "mouseMove",
      ...this.point(event),
      button: this.pressedButtons.values().next().value ?? "none",
      buttons: event.buttons,
      modifiers: modifiers(event),
      clickCount: 0,
    };
    this.lastPoint = { x: move.x, y: move.y };
    this.latestMove = move;
    this.animationFrame ??= requestAnimationFrame(() => this.flushMove());
  }

  private flushMove(): void {
    if (this.animationFrame !== undefined) cancelAnimationFrame(this.animationFrame);
    this.animationFrame = undefined;
    const move = this.latestMove;
    this.latestMove = undefined;
    if (move) this.enqueueMouse(move);
  }

  private enqueueMouse(params: MouseParams): void {
    this.inputQueue = this.inputQueue.then(() => this.session.sendMouse(params));
  }

  private sendKey(event: KeyboardEvent, type: "rawKeyDown" | "keyDown" | "keyUp"): void {
    const virtualKeyCode = windowsVirtualKeyCode(event);
    const text = type === "keyDown" ? keyText(event) : undefined;
    void this.session.sendKey({
      type,
      key: event.key,
      code: event.code,
      text,
      unmodifiedText: text,
      modifiers: modifiers(event),
      autoRepeat: event.repeat,
      windowsVirtualKeyCode: virtualKeyCode,
      nativeVirtualKeyCode: virtualKeyCode,
      location: event.location,
      isKeypad: event.location === KeyboardEvent.DOM_KEY_LOCATION_NUMPAD,
      isSystemKey: event.altKey,
    });
  }

  /**
   * Replay the patch stream onto the canvas, one event at a time.
   *
   * Order is the whole point: patches describe a difference against what the
   * canvas already shows, so overlapping them or letting a reset pass an
   * update paints a picture the browser never had.
   */
  private async applyCanvasEvents(canvas: HTMLCanvasElement): Promise<void> {
    if (this.patching) return;
    this.patching = true;
    try {
      for (let event = this.pendingCanvasEvents.shift(); event;) {
        if (event.kind === "reset") this.clearCanvas(canvas);
        else await this.paintPatches(canvas, event.update);
        event = this.pendingCanvasEvents.shift();
      }
    } catch (error) {
      this.session.reportError(error);
    } finally {
      this.patching = false;
    }
  }

  private clearCanvas(canvas: HTMLCanvasElement): void {
    const context = canvas.getContext("2d");
    if (!context) return;
    context.fillStyle = "#020304";
    context.fillRect(0, 0, canvas.width, canvas.height);
  }

  private async paintPatches(
    canvas: HTMLCanvasElement,
    update: DirtyRectangleUpdate,
  ): Promise<void> {
    // Resizing wipes the canvas, which is why the worker sends a whole canvas
    // whenever its size changes.
    if (canvas.width !== update.canvasWidth || canvas.height !== update.canvasHeight) {
      canvas.width = update.canvasWidth;
      canvas.height = update.canvasHeight;
    }
    const context = canvas.getContext("2d");
    if (!context) return;
    const bitmaps = await Promise.all(update.patches.map((patch) => createImageBitmap(patch.jpeg)));
    bitmaps.forEach((bitmap, index) => {
      const patch = update.patches[index];
      context.drawImage(bitmap, patch.x, patch.y);
      bitmap.close();
    });
  }

  private async renderLatestFrame(canvas: HTMLCanvasElement): Promise<void> {
    if (this.rendering) return;
    this.rendering = true;
    try {
      while (this.latestFrame) {
        const frame = this.latestFrame;
        this.latestFrame = undefined;
        const bitmap = await createImageBitmap(frame);
        if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
        }
        canvas.getContext("2d")?.drawImage(bitmap, 0, 0);
        bitmap.close();
      }
    } catch (error) {
      this.session.reportError(error);
    } finally {
      this.rendering = false;
    }
  }
}

function mouseButton(button: number): MouseParams["button"] {
  return MOUSE_BUTTONS[button] ?? "none";
}

function modifiers(event: MouseEvent | KeyboardEvent): number {
  return (
    Number(event.altKey) +
    Number(event.ctrlKey) * 2 +
    Number(event.metaKey) * 4 +
    Number(event.shiftKey) * 8
  );
}

function isShortcut(event: KeyboardEvent, key: string): boolean {
  return (event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === key;
}

const VIRTUAL_KEY: Readonly<Record<string, number>> = {
  Backspace: 8,
  Tab: 9,
  Enter: 13,
  NumpadEnter: 13,
  ShiftLeft: 16,
  ShiftRight: 16,
  ControlLeft: 17,
  ControlRight: 17,
  AltLeft: 18,
  AltRight: 18,
  Pause: 19,
  CapsLock: 20,
  Escape: 27,
  Space: 32,
  PageUp: 33,
  PageDown: 34,
  End: 35,
  Home: 36,
  ArrowLeft: 37,
  ArrowUp: 38,
  ArrowRight: 39,
  ArrowDown: 40,
  Insert: 45,
  Delete: 46,
  MetaLeft: 91,
  MetaRight: 92,
  ContextMenu: 93,
  NumpadMultiply: 106,
  NumpadAdd: 107,
  NumpadSubtract: 109,
  NumpadDecimal: 110,
  NumpadDivide: 111,
  NumLock: 144,
  ScrollLock: 145,
  Semicolon: 186,
  Equal: 187,
  Comma: 188,
  Minus: 189,
  Period: 190,
  Slash: 191,
  Backquote: 192,
  BracketLeft: 219,
  Backslash: 220,
  BracketRight: 221,
  Quote: 222,
};

function windowsVirtualKeyCode(event: KeyboardEvent): number {
  const mapped = VIRTUAL_KEY[event.code];
  if (mapped !== undefined) return mapped;
  if (/^Key[A-Z]$/.test(event.code)) return event.code.charCodeAt(3);
  if (/^Digit[0-9]$/.test(event.code)) return event.code.charCodeAt(5);
  if (/^Numpad[0-9]$/.test(event.code)) return 96 + Number(event.code.at(-1));
  if (/^F(?:[1-9]|1[0-9]|2[0-4])$/.test(event.code)) {
    return 111 + Number(event.code.slice(1));
  }
  return event.keyCode;
}

function keyText(event: KeyboardEvent): string | undefined {
  const hasAccelerator = event.altKey || event.ctrlKey || event.metaKey;
  if (event.key === "Enter" && !hasAccelerator) return "\r";
  if (event.key.length === 1 && (!hasAccelerator || event.getModifierState("AltGraph"))) {
    return event.key;
  }
  return undefined;
}
