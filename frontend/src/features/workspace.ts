import { queryClientContext } from "@tanstack/lit-query";
import { html } from "lit";
import { defineFeature, definePage, provide } from "lit-canon-composition";
import { AdminConsole } from "../app/admin/services/admin-console";
import { BrowserPersistenceVault } from "../app/browser/services/browser-persistence-vault";
import { ClientIdentity } from "../app/browser/services/client-identity";
import { ScreencastModeState } from "../app/browser/services/screencast-mode";
import {
  adminConsoleContext,
  appViewContext,
  clientIdentityContext,
  persistenceVaultContext,
  screencastModeContext,
} from "../app/shared/contexts";
import { AppViewState } from "../app/shell/view-mode";

export const workspaceFeature = defineFeature({
  name: "workspace",
  pages: [
    definePage({
      path: "/",
      load: () => import("../app/shell/app-shell"),
      render: () => html`<app-shell></app-shell>`,
    }),
  ],
  providers: [
    provide(clientIdentityContext, () => new ClientIdentity()),
    provide(screencastModeContext, () => new ScreencastModeState()),
    provide(appViewContext, () => new AppViewState()),
    provide(adminConsoleContext, (c) => new AdminConsole(c.get(queryClientContext))),
    provide(persistenceVaultContext, (c) => new BrowserPersistenceVault(c.get(queryClientContext))),
  ],
});
