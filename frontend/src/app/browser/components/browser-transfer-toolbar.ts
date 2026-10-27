import {
  downloadRecording,
  downloadSessionFile,
  listSessionDownloads,
  startRecording,
  stopRecording,
  type DownloadResponse,
  type RecordingResponse,
} from "@browsertunnel/backend-client";
import { signal, SignalWatcher } from "@lit-labs/signals";
import { ContextConsumer } from "@lit/context";
import { css, html, LitElement, nothing } from "lit";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import { browserSessionContext } from "../../shared/contexts";
import { errorMessage } from "../../shared/errors";
import { saveBlob } from "../../shared/file-download";
import { BrowserSession } from "../services/browser-session";
type Operation = "starting" | "stopping" | "video" | "refreshing" | "download";
type Notice = {
  readonly tone: "success" | "error";
  readonly text: string;
};
export class BrowserTransferToolbar extends SignalWatcher(LitElement) {
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
  protected readonly recording = signal<RecordingResponse | undefined>(undefined);
  protected readonly downloads = signal<readonly DownloadResponse[]>([]);
  protected readonly expanded = signal(false);
  protected readonly operation = signal<Operation | undefined>(undefined);
  protected readonly notice = signal<Notice | undefined>(undefined);
  protected get isRecording() {
    return this.recording.get()?.state === "recording";
  }
  protected get recordLabel() {
    switch (this.operation.get()) {
      case "starting":
        return "Starting…";
      case "stopping":
        return "Finishing…";
      case "video":
        return "Downloading…";
      default:
        break;
    }
    if (this.isRecording) return "Stop & download video";
    return this.recording.get() ? "Download video" : "Start recording";
  }
  protected toggleRecording(): void {
    if (this.isRecording) void this.stopAndSave();
    else if (this.recording.get()) void this.saveVideo();
    else void this.start();
  }
  protected toggleDownloads(): void {
    this.expanded.set(((value) => !value)(this.expanded.get()));
    if (this.expanded.get()) void this.refreshDownloads();
  }
  protected refreshDownloads(): Promise<void> {
    const sessionId = this.session.sessionId.get();
    if (!sessionId) return Promise.resolve();
    return this.run("refreshing", async () => {
      const response = await listSessionDownloads(sessionId);
      this.downloads.set(response);
      return undefined;
    });
  }
  protected saveDownload(download: DownloadResponse): Promise<void> {
    const sessionId = this.session.sessionId.get();
    if (!sessionId) return Promise.resolve();
    return this.run("download", async () => {
      const response = await downloadSessionFile(sessionId, download.id);
      if (!(response instanceof Blob)) throw new Error("File could not be downloaded");
      saveBlob(response, download.filename);
      return `${download.filename} downloaded`;
    });
  }
  protected fileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  private start(): Promise<void> {
    const browserId = this.session.browserId.get();
    if (!browserId) return Promise.resolve();
    return this.run("starting", async () => {
      const response = await startRecording(browserId);
      this.recording.set(response);
      return "Recording started";
    });
  }
  private stopAndSave(): Promise<void> {
    const browserId = this.session.browserId.get();
    const current = this.recording.get();
    if (!browserId || !current) return Promise.resolve();
    return this.run("stopping", async () => {
      const response = await stopRecording(browserId, current.id);
      this.recording.set(response);
      await this.saveRecording(browserId, response.id);
      return "Video downloaded";
    });
  }
  private saveVideo(): Promise<void> {
    const browserId = this.session.browserId.get();
    const current = this.recording.get();
    if (!browserId || !current) return Promise.resolve();
    return this.run("video", async () => {
      await this.saveRecording(browserId, current.id);
      return "Video downloaded";
    });
  }
  private async saveRecording(browserId: string, recordingId: string): Promise<void> {
    const response = await downloadRecording(browserId, recordingId);
    if (!(response instanceof Blob)) throw new Error("Video could not be downloaded");
    saveBlob(response, `recording-${recordingId}.mp4`);
  }
  private async run(
    operation: Operation,
    action: () => Promise<string | undefined>,
  ): Promise<void> {
    this.operation.set(operation);
    this.notice.set(undefined);
    try {
      const success = await action();
      if (success) this.notice.set({ tone: "success", text: success });
    } catch (error) {
      this.notice.set({ tone: "error", text: errorMessage(error, "Transfer failed") });
    } finally {
      this.operation.set(undefined);
    }
  }
  protected render() {
    return html` <div
        aria-label="Recordings and downloads"
        class=${classMap({ "transfer-bar": true })}
      >
        <button
          type="button"
          ?disabled=${!this.session.browserId.get() || !!this.operation.get()}
          class=${classMap({ "record-button": true, recording: Boolean(this.isRecording) })}
          @click=${(event: MouseEvent) => {
            this.toggleRecording();
          }}
        >
          <i aria-hidden="true"></i>${this.recordLabel}
        </button>

        <button
          type="button"
          aria-expanded=${this.expanded.get()}
          ?disabled=${!this.session.sessionId.get()}
          class=${classMap({ "downloads-button": true })}
          @click=${(event: MouseEvent) => {
            this.toggleDownloads();
          }}
        >
          Downloads <span>${this.downloads.get().length}</span>
          <svg
            viewBox="0 0 16 16"
            aria-hidden="true"
            class=${classMap({ open: Boolean(this.expanded.get()) })}
          >
            <path d="m5 6 3 3 3-3"></path>
          </svg>
        </button>

        ${((currentNotice) =>
          currentNotice
            ? html`
                <span
                  role="status"
                  data-tone=${currentNotice.tone}
                  class=${classMap({ notice: true })}
                >
                  ${currentNotice.text}
                </span>
              `
            : nothing)(this.notice.get())}
      </div>

      ${
        this.expanded.get()
          ? html`
              <section
                aria-label="Browser downloads"
                class=${classMap({ "downloads-popover": true })}
              >
                <header>
                  <span
                    ><strong>Browser downloads</strong
                    ><small>Files completed in this session.</small></span
                  >
                  <button
                    type="button"
                    ?disabled=${this.operation.get() === "refreshing"}
                    @click=${(event: MouseEvent) => {
                      this.refreshDownloads();
                    }}
                  >
                    ${this.operation.get() === "refreshing" ? "Refreshing…" : "Refresh"}
                  </button>
                </header>

                ${
                  this.downloads.get().length
                    ? html`
                        <ul>
                          ${repeat(
                            this.downloads.get(),
                            (download, index) => download.id,
                            (download, index) => html`
                              <li>
                                <span .title=${download.filename}>
                                  <strong>${download.filename}</strong
                                  ><small>${this.fileSize(download.size)}</small>
                                </span>
                                <button
                                  type="button"
                                  ?disabled=${!!this.operation.get()}
                                  @click=${(event: MouseEvent) => {
                                    this.saveDownload(download);
                                  }}
                                >
                                  Download
                                </button>
                              </li>
                            `,
                          )}
                        </ul>
                      `
                    : html` <p>No completed downloads yet.</p> `
                }
              </section>
            `
          : nothing
      }`;
  }
}
customElements.define("app-browser-transfer-toolbar", BrowserTransferToolbar);
