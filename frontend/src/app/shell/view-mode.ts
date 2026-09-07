import { Injectable, signal } from "@angular/core";

export const APP_VIEWS = ["browsers", "focus", "admin"] as const;
export type AppView = (typeof APP_VIEWS)[number];

const VIEW_PARAM = "view";
const DEFAULT_VIEW: AppView = "browsers";

@Injectable({ providedIn: "root" })
export class AppViewState {
  private readonly viewState = signal(readView());
  readonly view = this.viewState.asReadonly();

  constructor() {
    window.history.replaceState(null, "", urlFor(this.viewState()));
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

function urlFor(view: AppView): string {
  const url = new URL(window.location.href);
  url.searchParams.set(VIEW_PARAM, view);
  return `${url.pathname}${url.search}${url.hash}`;
}
