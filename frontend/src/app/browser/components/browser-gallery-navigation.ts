import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

@Component({
  selector: "app-browser-gallery-navigation",
  template: `
    <button
      class="gallery-arrow previous"
      type="button"
      aria-label="Show previous browser"
      (click)="previous.emit()"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5-7 7 7 7" /></svg>
    </button>
    <button
      class="gallery-arrow next"
      type="button"
      aria-label="Show next browser"
      (click)="next.emit()"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
    </button>
    <nav class="gallery-dots" aria-label="Select browser">
      @for (item of items(); track item; let index = $index) {
        <button
          type="button"
          [class.active]="activeIndex() === index"
          [attr.aria-label]="'Show browser ' + (index + 1)"
          [attr.aria-current]="activeIndex() === index ? 'true' : null"
          (click)="show.emit(index)"
        ></button>
      }
    </nav>
  `,
  styles: `
    :host {
      display: contents;
    }
    .gallery-arrow {
      position: absolute;
      z-index: 10;
      top: 50%;
      display: grid;
      place-items: center;
      width: 42px;
      height: 56px;
      padding: 0;
      color: #dbe4f4;
      background: rgb(18 23 31 / 86%);
      border: 1px solid #333d4d;
      border-radius: 12px;
      box-shadow: 0 12px 32px rgb(0 0 0 / 35%);
      backdrop-filter: blur(12px);
      cursor: pointer;
      transform: translateY(-50%);
      transition:
        color 180ms ease,
        background 180ms ease,
        transform 180ms ease;
    }
    .gallery-arrow:hover {
      color: #fff;
      background: #263043;
      transform: translateY(-50%) scale(1.04);
    }
    .gallery-arrow.previous {
      left: clamp(8px, 1.4vw, 20px);
    }
    .gallery-arrow.next {
      right: clamp(8px, 1.4vw, 20px);
    }
    .gallery-arrow svg {
      width: 23px;
      height: 23px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.8;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .gallery-dots {
      position: absolute;
      z-index: 10;
      bottom: 38px;
      left: 50%;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 7px;
      min-height: 26px;
      padding: 0 11px;
      background: rgb(12 16 22 / 76%);
      border: 1px solid rgb(68 79 96 / 58%);
      border-radius: 999px;
      box-shadow: 0 8px 24px rgb(0 0 0 / 28%);
      backdrop-filter: blur(10px);
      transform: translateX(-50%);
    }
    .gallery-dots button {
      width: 7px;
      height: 7px;
      padding: 0;
      background: #394252;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      transition:
        width 240ms ease,
        background 240ms ease;
    }
    .gallery-dots button.active {
      width: 24px;
      background: #759df3;
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 2px;
    }
    @media (max-width: 580px) {
      .gallery-arrow {
        width: 36px;
        height: 46px;
        border-radius: 10px;
      }
      .gallery-arrow.previous {
        left: 6px;
      }
      .gallery-arrow.next {
        right: 6px;
      }
      .gallery-dots {
        bottom: 36px;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .gallery-arrow,
      .gallery-dots button {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserGalleryNavigation {
  readonly items = input.required<readonly string[]>();
  readonly activeIndex = input.required<number>();
  readonly previous = output<void>();
  readonly next = output<void>();
  readonly show = output<number>();
}
