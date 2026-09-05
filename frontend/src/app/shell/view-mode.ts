import { Injectable, signal } from "@angular/core";

export const APP_VIEWS = ["browsers", "admin"] as const;
export type AppView = (typeof APP_VIEWS)[number];

const VIEW_PARAM = "view";
const DEFAULT_VIEW: AppView = "browsers";

/**
 * The open tab, kept in the address bar.
 *
 * A view is a place, not a preference: sharing the link to the admin tab, or
 * reloading while looking at it, has to land where you were. The parameter is
 * written back on startup too, so the URL always says which tab is open.
 */
@Injectable({ providedIn: "root" })
export class AppViewState {
  private readonly viewState = signal(readView());
  readonly view = this.viewState.asReadonly();

  constructor() {
    window.history.replaceState(null, "", urlFor(this.viewState()));
    // Back and forward move between tabs rather than out of the app.
    window.addEventListener("popstate", () => this.viewState.set(readView()));
  }

  select(view: AppView): void {
    if (view === this.viewState()) return;
    this.viewState.set(view);
    window.history.pushState(null, "", urlFor(view));
  }
}

function readView(): AppView {
  const value = new URLSearchParams(window.location.search).get(VIEW_PARAM);
  return isAppView(value) ? value : DEFAULT_VIEW;
}

function isAppView(value: string | null): value is AppView {
  return APP_VIEWS.includes(value as AppView);
}

/** Keep every other parameter — the screencast mode rides along in the URL too. */
function urlFor(view: AppView): string {
  const url = new URL(window.location.href);
  url.searchParams.set(VIEW_PARAM, view);
  return `${url.pathname}${url.search}${url.hash}`;
}
