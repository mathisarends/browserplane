import type { MouseParams } from "@browsertunnel/browser-rpc-client/models";
import { SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement } from "lit";
import { styleMap } from "lit/directives/style-map.js";
import { browserSessionContext } from "../../shared/contexts";
import { BrowserSession } from "../services/browser-session";
import { CanvasPainter } from "../services/canvas-painter";
import {
  isClipboardShortcut,
  keyParams,
  mouseButtonOf,
  mouseParams,
  releaseMouseParams,
  type MousePoint,
} from "../services/input-events";
export class BrowserCanvas extends SignalWatcher(LitElement) {
  static styles = [
    css`
      :host,
      * {
        box-sizing: border-box;
      }
      button,
      input,
      select {
        font: inherit;
      }
    `,
    css`
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
  ];
  private readonly sessionConsumer = new ContextConsumer(this, {
    context: browserSessionContext,
    subscribe: true,
  });
  protected get session(): BrowserSession {
    const value = this.sessionConsumer.value;
    if (!value) throw new Error("Missing BrowserSession provider");
    return value;
  }
  private get canvas(): HTMLCanvasElement | undefined {
    return this.renderRoot.querySelector<HTMLCanvasElement>('[data-ref="canvas"]') ?? undefined;
  }
  private painter?: CanvasPainter;
  private readonly heldButtons = new Map<number, MouseParams["button"]>();
  private pendingMove?: MouseParams;
  private moveFrame?: number;
  private lastPoint?: MousePoint;
  protected get cursor() {
    return this.session.page.cursor.get();
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("mouseup", this.handlemouseup);
    window.removeEventListener("mousemove", this.handlemousemove);
    window.removeEventListener("blur", this.handleblur);
    document.removeEventListener("paste", this.handlepaste);
    if (this.moveFrame !== undefined) cancelAnimationFrame(this.moveFrame);
  }
  protected onMouseDown(event: MouseEvent): void {
    event.preventDefault();
    this.canvas?.focus();
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
    if ((this.renderRoot as ShadowRoot).activeElement !== this.canvas) return;
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
    const canvas = this.canvas;
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
    void this.session.sendMouse(params);
  }
  private async paint(work: () => Promise<void>): Promise<void> {
    try {
      await work();
    } catch (error) {
      this.session.reportError(error);
    }
  }
  private lastFrame?: Blob;
  protected updated(): void {
    const frame = this.session.stream.frame.get();
    this.session.stream.tick.get();
    this.painter ??= new CanvasPainter(this.canvas!);
    if (frame && frame !== this.lastFrame) {
      this.lastFrame = frame;
      void this.paint(() => this.painter!.draw(frame));
    }
    void this.paint(() => this.painter!.replay(this.session.stream.take()));
  }
  private readonly handlemouseup = (event: MouseEvent) => {
    this.onMouseUp(event);
  };
  private readonly handlemousemove = (event: MouseEvent) => {
    this.onWindowMouseMove(event);
  };
  private readonly handleblur = (event: Event) => {
    this.releaseHeldButtons();
  };
  private readonly handlepaste = (event: ClipboardEvent) => {
    this.onPaste(event);
  };
  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("mouseup", this.handlemouseup);
    window.addEventListener("mousemove", this.handlemousemove);
    window.addEventListener("blur", this.handleblur);
    document.addEventListener("paste", this.handlepaste);
  }
  protected render() {
    return html`
      <canvas
        width="1600"
        height="900"
        tabindex="0"
        aria-label="Browser stream"
        data-ref="canvas"
        style=${styleMap({ cursor: this.cursor })}
        @mousedown=${(event: MouseEvent) => {
          this.onMouseDown(event);
        }}
        @mousemove=${(event: MouseEvent) => {
          this.onCanvasMouseMove(event);
        }}
        @mouseleave=${(event: MouseEvent) => {
          this.onCanvasMouseMove(event);
        }}
        @contextmenu=${(event: Event) => {
          event.preventDefault();
        }}
        @wheel=${(event: WheelEvent) => {
          this.onWheel(event);
        }}
        @keydown=${(event: KeyboardEvent) => {
          this.onKeyDown(event);
        }}
        @keyup=${(event: KeyboardEvent) => {
          this.onKeyUp(event);
        }}
      ></canvas>
    `;
  }
}
customElements.define("app-browser-canvas", BrowserCanvas);
