import { createContext } from "@lit/context";
import type { AdminConsole } from "../admin/services/admin-console";
import type { BrowserPersistenceVault } from "../browser/services/browser-persistence-vault";
import type { BrowserSession } from "../browser/services/browser-session";
import type { ClientIdentity } from "../browser/services/client-identity";
import type { ScreencastModeState } from "../browser/services/screencast-mode";
import type { AppViewState } from "../shell/view-mode";

export const adminConsoleContext = createContext<AdminConsole>(Symbol("admin-console"));
export const persistenceVaultContext = createContext<BrowserPersistenceVault>(
  Symbol("persistence-vault"),
);
export const browserSessionContext = createContext<BrowserSession>(Symbol("browser-session"));
export const clientIdentityContext = createContext<ClientIdentity>(Symbol("client-identity"));
export const screencastModeContext = createContext<ScreencastModeState>(Symbol("screencast-mode"));
export const appViewContext = createContext<AppViewState>(Symbol("app-view"));
