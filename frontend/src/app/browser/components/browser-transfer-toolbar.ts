import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import {
  downloadRecording,
  downloadSessionFile,
  listSessionDownloads,
  startRecording,
  stopRecording,
  type DownloadResponse,
  type RecordingResponse,
} from "@browsertunnel/backend-client";
import { BrowserSession } from "../services/browser-session";

type Operation = "starting" | "stopping" | "video" | "refreshing" | "download";
type Notice = { readonly tone: "success" | "error"; readonly text: string };

@Component({
  selector: "app-browser-transfer-toolbar",
  template: `
    <div class="transfer-bar" aria-label="Recordings and downloads">
      <button
        class="record-button"
        type="button"
        [class.recording]="recording()?.state === 'recording'"
        [disabled]="!session.browserId() || !!operation()"
        (click)="recording()?.state === 'recording' ? stop() : recording() ? saveVideo() : start()"
      >
        <i aria-hidden="true"></i>
        @if (operation() === "starting") {
          Starting…
        } @else if (operation() === "stopping") {
          Finishing…
        } @else if (operation() === "video") {
          Downloading…
        } @else if (recording()?.state === "recording") {
          Stop & download video
        } @else if (recording()?.state === "completed") {
          Download video
        } @else {
          Start recording
        }
      </button>

      <button
        class="downloads-button"
        type="button"
        [attr.aria-expanded]="expanded()"
        [disabled]="!session.sessionId()"
        (click)="toggleDownloads()"
      >
        Downloads <span>{{ downloads().length }}</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" [class.open]="expanded()">
          <path d="m5 6 3 3 3-3" />
        </svg>
      </button>

      @if (notice(); as currentNotice) {
        <span class="notice" [attr.data-tone]="currentNotice.tone" role="status">
          {{ currentNotice.text }}
        </span>
      }
    </div>

    @if (expanded()) {
      <section class="downloads-popover" aria-label="Browser downloads">
        <header>
          <span
            ><strong>Browser downloads</strong><small>Files completed in this session.</small></span
          >
          <button
            type="button"
            [disabled]="operation() === 'refreshing'"
            (click)="refreshDownloads()"
          >
            {{ operation() === "refreshing" ? "Refreshing…" : "Refresh" }}
          </button>
        </header>

        @if (downloads().length) {
          <ul>
            @for (download of downloads(); track download.id) {
              <li>
                <span [title]="download.filename">
                  <strong>{{ download.filename }}</strong
                  ><small>{{ fileSize(download.size) }}</small>
                </span>
                <button type="button" [disabled]="!!operation()" (click)="saveDownload(download)">
                  Download
                </button>
              </li>
            }
          </ul>
        } @else {
          <p>No completed downloads yet.</p>
        }
      </section>
    }
  `,
  styles: `
    :host {
      position: relative;
      z-index: 13;
      display: block;
    }
    .transfer-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      padding: 4px 8px;
      color: #858b95;
      font: 0.66rem/1 var(--font-mono);
      background: #121419;
      border-top: 1px solid #292c33;
    }
    button {
      min-height: 25px;
      padding: 0 9px;
      color: #aeb4be;
      font: inherit;
      background: #1d2026;
      border: 1px solid #323640;
      border-radius: 7px;
      cursor: pointer;
    }
    button:hover:not(:disabled) {
      color: #f1f3f5;
      background: #292d35;
    }
    button:focus-visible {
      outline: 2px solid #79a4ff;
      outline-offset: 1px;
    }
    button:disabled {
      opacity: 0.48;
      cursor: default;
    }
    .record-button,
    .downloads-button {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .record-button i {
      width: 7px;
      height: 7px;
      background: #d56761;
      border-radius: 50%;
    }
    .record-button.recording {
      color: #f2b7b3;
      border-color: #713c3a;
      background: #2b1c1e;
    }
    .record-button.recording i {
      border-radius: 1px;
      box-shadow: 0 0 0 3px rgb(213 103 97 / 12%);
    }
    .downloads-button span {
      min-width: 17px;
      padding: 2px 5px;
      text-align: center;
      background: #2a2e36;
      border-radius: 999px;
    }
    .downloads-button svg {
      width: 12px;
      height: 12px;
      fill: none;
      stroke: currentcolor;
      stroke-width: 1.5;
      transition: transform 160ms ease;
    }
    .downloads-button svg.open {
      transform: rotate(180deg);
    }
    .notice {
      overflow: hidden;
      margin-left: auto;
      color: #72a881;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .notice[data-tone="error"] {
      color: #d17a73;
    }
    .downloads-popover {
      position: absolute;
      right: 8px;
      bottom: calc(100% + 6px);
      left: 8px;
      display: grid;
      gap: 10px;
      padding: 12px;
      background: rgb(22 24 29 / 98%);
      border: 1px solid #373a43;
      border-radius: 12px;
      box-shadow: 0 20px 56px rgb(0 0 0 / 52%);
      backdrop-filter: blur(18px);
    }
    .downloads-popover header,
    .downloads-popover li {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .downloads-popover header > span,
    .downloads-popover li > span {
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .downloads-popover strong {
      overflow: hidden;
      color: #e4e7eb;
      font-size: 0.72rem;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .downloads-popover small,
    .downloads-popover p {
      margin: 0;
      color: #747a84;
      font-size: 0.64rem;
    }
    .downloads-popover ul {
      display: grid;
      gap: 6px;
      max-height: 190px;
      padding: 0;
      margin: 0;
      overflow: auto;
      list-style: none;
    }
    .downloads-popover li {
      padding: 7px;
      background: #1a1d23;
      border: 1px solid #2c3038;
      border-radius: 8px;
    }
    @media (max-width: 580px) {
      .notice {
        display: none;
      }
      .record-button {
        flex: 1;
        justify-content: center;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .downloads-button svg {
        transition: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserTransferToolbar {
  protected readonly session = inject(BrowserSession);
  protected readonly recording = signal<RecordingResponse | undefined>(undefined);
  protected readonly downloads = signal<readonly DownloadResponse[]>([]);
  protected readonly expanded = signal(false);
  protected readonly operation = signal<Operation | undefined>(undefined);
  protected readonly notice = signal<Notice | undefined>(undefined);

  protected async start(): Promise<void> {
    const browserId = this.session.browserId();
    if (!browserId) return;
    this.operation.set("starting");
    this.notice.set(undefined);
    try {
      const response = await startRecording(browserId);
      if (response.status !== 201)
        throw apiError("Recording could not be started", response.status);
      this.recording.set(response.data);
      this.notice.set({ tone: "success", text: "Recording started" });
    } catch (error) {
      this.fail(error);
    } finally {
      this.operation.set(undefined);
    }
  }

  protected async stop(): Promise<void> {
    const browserId = this.session.browserId();
    const current = this.recording();
    if (!browserId || !current) return;
    this.operation.set("stopping");
    this.notice.set(undefined);
    try {
      const response = await stopRecording(browserId, current.id);
      if (response.status !== 200)
        throw apiError("Recording could not be stopped", response.status);
      this.recording.set(response.data);
      await this.fetchVideo(browserId, response.data.id);
      this.notice.set({ tone: "success", text: "Video downloaded" });
    } catch (error) {
      this.fail(error);
    } finally {
      this.operation.set(undefined);
    }
  }

  protected async saveVideo(): Promise<void> {
    const browserId = this.session.browserId();
    const current = this.recording();
    if (!browserId || !current) return;
    this.operation.set("video");
    this.notice.set(undefined);
    try {
      await this.fetchVideo(browserId, current.id);
      this.notice.set({ tone: "success", text: "Video downloaded" });
    } catch (error) {
      this.fail(error);
    } finally {
      this.operation.set(undefined);
    }
  }

  protected toggleDownloads(): void {
    this.expanded.update((value) => !value);
    if (this.expanded()) void this.refreshDownloads();
  }

  protected async refreshDownloads(): Promise<void> {
    const sessionId = this.session.sessionId();
    if (!sessionId) return;
    this.operation.set("refreshing");
    this.notice.set(undefined);
    try {
      const response = await listSessionDownloads(sessionId);
      if (response.status !== 200) throw apiError("Downloads could not be loaded", response.status);
      this.downloads.set(response.data);
    } catch (error) {
      this.fail(error);
    } finally {
      this.operation.set(undefined);
    }
  }

  protected async saveDownload(download: DownloadResponse): Promise<void> {
    const sessionId = this.session.sessionId();
    if (!sessionId) return;
    this.operation.set("download");
    this.notice.set(undefined);
    try {
      const response = await downloadSessionFile(sessionId, download.id);
      if (response.status !== 200 || !(response.data instanceof Blob)) {
        throw apiError("File could not be downloaded", response.status);
      }
      saveBlob(response.data, download.filename);
      this.notice.set({ tone: "success", text: `${download.filename} downloaded` });
    } catch (error) {
      this.fail(error);
    } finally {
      this.operation.set(undefined);
    }
  }

  protected fileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  private async fetchVideo(browserId: string, recordingId: string): Promise<void> {
    const response = await downloadRecording(browserId, recordingId);
    if (response.status !== 200 || !(response.data instanceof Blob)) {
      throw apiError("Video could not be downloaded", response.status);
    }
    saveBlob(response.data, `recording-${recordingId}.mp4`);
  }

  private fail(error: unknown): void {
    this.notice.set({
      tone: "error",
      text: error instanceof Error ? error.message : "Transfer failed",
    });
  }
}

function apiError(message: string, status: number): Error {
  return new Error(`${message} (${status})`);
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
