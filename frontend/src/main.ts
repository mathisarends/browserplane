import { QueryClient, queryClientContext } from "@tanstack/lit-query";
import { html } from "lit";
import { createApp, provide } from "lit-canon-composition";
import { configureApiFetch } from "lit-canon-fetch";
import "urlpattern-polyfill";
import { workspaceFeature } from "./features/workspace";
import "./style.css";

configureApiFetch({ baseUrl: "", credentials: "same-origin" });
const root = document.querySelector("#app");
if (!root) throw new Error("Missing application root");
createApp({
  root,
  features: [workspaceFeature],
  baseTitle: "Browserplane",
  providers: [provide(queryClientContext, () => new QueryClient())],
  notFound: () => html`<p>Page not found. <a href="/">Open Browserplane</a></p>`,
}).start();
