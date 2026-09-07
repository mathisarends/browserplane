import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { BrowserSession } from "../services/browser-session";

@Component({
  selector: "app-browser-stream-badge",
  template: `
    @if (stream(); as state) {
      <p class="stream-badge" [attr.data-state]="state.complete ? 'complete' : 'partial'">
        <i aria-hidden="true"></i>
        <strong>dirty rectangles</strong>
        <span>{{ state.coveredTiles }}/{{ state.tiles }} tiles</span>
        <span>{{ state.packets }} packets · {{ state.patches }} patches</span>
        <span>{{ megabytes() }} MB</span>
        @if (state.resyncs) {
          <span>{{ state.resyncs }} resyncs</span>
        }
        @if (!state.connected) {
          <span>reconnecting</span>
        }
      </p>
    }
  `,
  styles: `
    :host {
      display: block;
    }

    .stream-badge {
      display: flex;
      flex-wrap: wrap;
      gap: 0 12px;
      margin: 0;
      padding: 6px 12px;
      color: #8d9bb2;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      background: #0d1117;
      border-top: 1px solid #1d2530;
    }

    strong {
      color: #c6d3e6;
      font-weight: 600;
    }

    i {
      align-self: center;
      width: 7px;
      height: 7px;
      background: #f0a63c;
      border-radius: 50%;
    }

    .stream-badge[data-state="complete"] i {
      background: #4ec98a;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserStreamBadge {
  private readonly session = inject(BrowserSession);
  protected readonly stream = this.session.stream.dirtyRectangles;
  protected readonly megabytes = computed(() =>
    ((this.stream()?.bytes ?? 0) / 1_048_576).toFixed(2),
  );
}
