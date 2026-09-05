# Browser State im Browser Worker

Ziel: Den kompletten wiederherstellbaren Zustand eines Browsers aus einer
laufenden Session **auslesen**, außerhalb aufbewahren und später auf einen
frisch provisionierten Browser wieder **aufspielen** — sowohl den
Anmeldezustand (Cookies + localStorage) als auch den Arbeitszustand (offene
Tabs, deren URLs, sessionStorage und Scrollposition, aktiver Tab).

Diese Spec ist so geschrieben, dass sie ohne Rückfragen umgesetzt werden kann:
alle offenen Entscheidungen sind unten getroffen und begründet.

## 0. Vorlagen und was davon übernommen wird

Zwei Codestücke standen Pate, beide aus anderen Projekten:

- `BrowserStorageStateManager` (browsertunnel) — Cookies + localStorage über
  den `FocusedTabClient`.
- `BrowserStateManager` / `BrowserTabs` (vizron) — Tabs, sessionStorage,
  Scroll, Restore-Script.

Beide hängen an Infrastruktur, die es im Browser Worker nicht gibt
(`FocusedTabClient`, `EventBus`, `SecurityPolicy`, eine langlebige
`BrowserTabs`-Registry). Übernommen wird das **Verfahren**, nicht die
Aufhängung. Die konkreten Abweichungen stehen in Abschnitt 9.

Wichtige Randbedingung, die vieles vereinfacht: `ChromeProcess.start()` liefert
den **Browser-Level-Endpoint** (`ws://127.0.0.1:<port>/devtools/browser/<id>`).
Es gibt hier also kein "root target", an das die Verbindung gebunden wäre —
jede Page ist gleichberechtigt und wird über `Target.attachToTarget` zu einer
`CDPSession`. Der ganze `root_target_id`-Sonderfall aus vizron entfällt.

## 1. Datenmodell

Zwei Ebenen, die getrennt bleiben, weil man den Auth-Zustand oft ohne die Tabs
weiterreichen will:

```python
# application/models.py


@dataclass(frozen=True, slots=True)
class LocalStorageItem:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class BrowserOriginState:
    """Der localStorage einer Origin."""

    origin: str
    local_storage: tuple[LocalStorageItem, ...] = ()


@dataclass(frozen=True, slots=True)
class BrowserCookie:
    name: str
    value: str
    domain: str
    path: str
    expires: float | None = None
    http_only: bool = False
    secure: bool = False
    same_site: str | None = None


@dataclass(frozen=True, slots=True)
class AuthenticationState:
    """Was einen Browser eingeloggt macht: Cookies und localStorage."""

    cookies: tuple[BrowserCookie, ...] = ()
    origins: tuple[BrowserOriginState, ...] = ()


@dataclass(frozen=True, slots=True)
class ScrollPosition:
    x: int = 0
    y: int = 0


@dataclass(frozen=True, slots=True)
class BrowserTabState:
    """Ein Tab, so wie er wiederhergestellt werden kann."""

    url: str
    scroll: ScrollPosition = ScrollPosition()
    session_storage: tuple[LocalStorageItem, ...] = ()


@dataclass(frozen=True, slots=True)
class BrowserState:
    """Der vollständige wiederherstellbare Zustand eines Browsers."""

    tabs: tuple[BrowserTabState, ...] = ()
    active_tab_index: int = 0
    authentication: AuthenticationState = AuthenticationState()
```

Entscheidungen dazu:

- **`AuthenticationState` ist Playwright-förmig** (`cookies` +
  `origins[].localStorage`). Damit lässt sich der Auth-Teil ohne Konvertierung
  in Playwright/Patchright einspeisen und aus einem Playwright-`storage_state`
  übernehmen. Nur der Auth-Teil — `tabs` ist unsere Erweiterung.
- **`session_storage` ist eine Liste von Items, kein Dict**, anders als in
  vizron. Grund: gleiche Form wie `local_storage`, stabile Reihenfolge im
  JSON, und ein Dict mit beliebigen Keys ist im OpenAPI-Schema (und damit im
  generierten TS-Client) unangenehmer als eine Liste.
- **Keine `target_id` im State.** Target-IDs sind pro Browserprozess vergeben
  und nach einem Neustart wertlos. Tabs sind eine geordnete Liste, der aktive
  Tab ein Index in diese Liste.
- **Domain bleibt snake_case Dataclasses.** Das Playwright-Casing
  (`httpOnly`, `sameSite`, `localStorage`, `sessionStorage`) lebt
  ausschließlich in den Pydantic-Schemas der Presentation-Schicht über `alias`
  + `populate_by_name`. Der Mapper übersetzt. (Die Vorlage aus browsertunnel
  mischt beides — `localStorage=` schreiben, `origin.local_storage` lesen — das
  wird hier nicht übernommen.)
- **Alles hat Defaults**, `BrowserState()` ist gültig und bedeutet "leerer
  Browser". Ein Mount mit `tabs=()` lässt die Tabs unangetastet und spielt nur
  den Auth-Zustand auf (siehe 7.1).

## 2. API

```
GET  /api/v1/browser/{browser_id}/state      -> BrowserStateResponse
PUT  /api/v1/browser/{browser_id}/state      -> 204 No Content
```

- `GET` = capture. Optionaler Query-Parameter
  `?origins=https://a.example&origins=https://b.example`, um zusätzlich
  Origins auszulesen, die gerade in keinem Tab offen sind (siehe 6.2).
- `PUT` = mount. Der Body ist exakt der Response-Body von `GET`, der Roundtrip
  ist also verlustfrei und der Endpoint idempotent. `PUT` statt `POST`, weil
  der Aufruf den Zustand ersetzt und nichts anlegt.
- Beide Endpunkte liegen unter `browser/{browser_id}` wie `recordings` auch,
  und `browser_id` wird gegen den laufenden Browser geprüft.

Fehler:

| Code | Status | Wann |
| --- | --- | --- |
| `BROWSER_NOT_FOUND` | 404 | `browser_id` gehört nicht zum laufenden Browser (bestehender Spec aus `browsers`, wiederverwenden) |
| `BROWSER_STATE_INVALID` | 422 | Body ist strukturell ok, aber inhaltlich nicht mountbar (unerlaubtes URL-Schema, `active_tab_index` außerhalb `tabs`) |
| `BROWSER_STATE_FAILED` | 503 | CDP hat die Operation nicht ausgeführt |

Die beiden neuen Codes kommen in `ApiErrorCode`
(`browser_worker/presentation/errors.py`).

**Bewusst nicht** in `CreateBrowserRequest` mit hineingezogen: `create_browser`
würde damit zwei Dinge tun und im Fehlerfall einen halb hochgefahrenen Browser
hinterlassen. Der Provisioner im Control Plane macht zwei Calls —
`create_browser`, danach `mount_browser_state` — und kann den zweiten Schritt
sauber behandeln.

## 3. Feature-Layout

Ein eigenes Feature `browser_state`, geschnitten wie `recordings`:

```
browser_worker/src/browser_worker/features/browser_state/
  application/
    models.py       (Abschnitt 1)
    ports.py        BrowserStateStore
    exceptions.py   BrowserStateFailedException, BrowserStateInvalidException
    service.py      BrowserStateService
  infrastructure/
    cdp_state.py    CdpBrowserStateStore
    scripts.py      Capture-Expression + Restore-Script-Builder
  presentation/
    schemas.py, mapper.py, router.py, errors.py
  provider.py       BrowserStateProvider
```

`browsers` bleibt für Prozess-Lifecycle, CDP-Proxy und Screencast zuständig.

## 4. Port

```python
# application/ports.py


class BrowserStateStore(ABC):
    """Liest und schreibt den wiederherstellbaren Zustand eines Browsers."""

    @abstractmethod
    async def capture(self, extra_origins: Sequence[str] = ()) -> BrowserState: ...

    @abstractmethod
    async def restore(self, state: BrowserState) -> None: ...
```

`restore` ist immer "ersetzen" — es gibt kein `merge`-Flag. Ein Mount, der den
vorhandenen Zustand stehen lässt, wäre nicht reproduzierbar und niemand
braucht ihn.

## 5. Service

```python
StateStoreFactory = Callable[[str], BrowserStateStore]


class BrowserStateService:
    def __init__(
        self, browsers: BrowserService, store_factory: StateStoreFactory
    ) -> None:
        self._browsers = browsers
        self._store_factory = store_factory

    async def capture(
        self, browser_id: UUID, origins: Sequence[str] = ()
    ) -> BrowserState:
        store = self._store_factory(self._browsers.upstream_cdp_url(browser_id))
        return await store.capture(extra_origins=origins)

    async def mount(self, browser_id: UUID, state: BrowserState) -> None:
        _validate(state)
        store = self._store_factory(self._browsers.upstream_cdp_url(browser_id))
        await store.restore(state)
```

- `upstream_cdp_url` wirft bereits `BrowserNotFoundException` — kein eigener
  Not-Found nötig.
- **Kein State im Service, kein Lock.** Beide Operationen sind gegenüber dem
  Worker zustandslos; der Zustand lebt im Browser. Damit gibt es auch kein
  `_restored`-Flag wie in vizron: dort ist `restore()` ein einmaliger
  Bootstrap, hier ein explizit aufgerufener Endpoint, der beliebig oft laufen
  darf.
- `_validate` prüft URL-Schemata und `active_tab_index` und wirft
  `BrowserStateInvalidException` (siehe 8.2).
- `StateStoreFactory` wird im `BrowserStateProvider` gebunden, genau wie
  `RecorderFactory` im `RecordingProvider`.

## 6. Capture

`CdpBrowserStateStore` bekommt die `upstream_cdp_url` und öffnet **pro
Operation** einen kurzlebigen `cdpify.Client` (`async with Client(url)`), der
am Ende wieder geschlossen wird. Kein Anschluss an `ActiveTabStreams`: der
Screencast-Stream existiert wegen der Sichtbarkeits-Events; wir wollen keinen
Screencast starten, nur um Cookies zu lesen.

Reihenfolge: Cookies und Tab-Capture können parallel laufen
(`asyncio.gather`), die Origin-Ermittlung hängt an der Target-Liste.

### 6.1 Cookies

Browserweit über die Storage-Domain statt über eine Page-Session:

```python
result = await client.storage.get_cookies()  # list[network.Cookie]
```

Das ersetzt `Network.getAllCookies` aus der Vorlage: der Aufruf ist nicht an
einen Tab gebunden und liefert den kompletten Browser-Kontext. Beim Mappen
wird `expires <= 0` (Session-Cookie) auf `None` normalisiert.

### 6.2 Welche Origins für localStorage?

`DOMStorage.getDOMStorageItems` braucht eine konkrete `StorageId`, und CDP hat
keine Methode "gib mir alle Origins mit localStorage". Origins kommen deshalb
aus zwei Quellen:

1. **Offene Page-Targets**: `client.target.get_targets()`, gefiltert auf
   `type == "page"` und URLs mit Schema `http`/`https`, reduziert auf
   `scheme://netloc`. Das deckt den realistischen Fall ab (in den offenen Tabs
   wurde eingeloggt) und ist deutlich mehr als die Vorlage kann, die nur den
   fokussierten Tab liest.
2. **Explizite Origins** aus dem Query-Parameter.

Dann pro Origin:

```python
await client.dom_storage.get_dom_storage_items(
    storage_id=StorageId(security_origin=origin, is_local_storage=True)
)
```

Die `DOMStorage`-Domain ist browserweit erreichbar (kein Session-Attach
nötig). Origins ohne Einträge werden verworfen, damit der State nicht mit
leeren Objekten aufgebläht wird. Die Origin-Liste wird dedupliziert und
sortiert, damit zwei Captures desselben Zustands byte-gleich sind.

### 6.3 Tabs

Für jedes Page-Target aus `get_targets()`, in der Reihenfolge, die CDP
liefert:

1. `client.target.attach_to_target(target_id=..., flatten=True)` →
   `session_id`, daraus `client.session(session_id)`.
2. `session.runtime.evaluate(expression=_CAPTURE_EXPRESSION,
   return_by_value=True, silent=True)`.
3. `client.target.detach_from_target(session_id=...)`.

Die Capture-Expression (in `infrastructure/scripts.py`) liefert URL,
Scrollposition und sessionStorage in einem Roundtrip:

```js
(() => {
    let sessionStorage = [];
    try {
        sessionStorage = Array.from(
            {length: window.sessionStorage.length},
            (_, index) => {
                const name = window.sessionStorage.key(index);
                return {name, value: window.sessionStorage.getItem(name)};
            },
        ).filter((item) => item.name !== null);
    } catch (_) {}

    return {
        url: window.location.href,
        scroll: {
            x: Math.max(0, Math.round(window.scrollX)),
            y: Math.max(0, Math.round(window.scrollY)),
        },
        session_storage: sessionStorage,
        visible: document.visibilityState === "visible",
    };
})()
```

Fehlerbehandlung pro Tab, aus der vizron-Vorlage übernommen: schlägt das
`evaluate` fehl (cross-origin, Target gerade weg, Interstitial), fällt der Tab
auf `BrowserTabState(url=<target.url>)` zurück, wenn die Target-URL nicht leer
ist — sonst wird der Tab ausgelassen. Ein kaputter Tab darf den Capture nicht
kippen.

Tabs auf `about:blank`, `chrome://…` und Ähnliches werden ausgelassen: sie
sind nicht wiederherstellbar und ein leerer Tab beim Restore ist ohnehin der
Ausgangszustand.

`active_tab_index`: die Capture-Expression liefert zusätzlich
`visible: document.visibilityState === "visible"`; der erste sichtbare Tab wird
zum `active_tab_index`, findet sich keiner, ist es `0`. `ActiveTabStreams`
wüsste das zwar auch, wird aber bewusst nicht benutzt — ein Abo dort startet
einen Screencast, und das ist für einen Capture zu teuer.

## 7. Restore

Die Reihenfolge ist der entscheidende Teil und muss genau so eingehalten
werden:

```
1. Cookies löschen und setzen          (browserweit)
2. localStorage pro Origin schreiben   (Hintergrund-Tabs, siehe 7.2)
3. Tabs herstellen                     (navigieren, siehe 7.3)
4. Aktiven Tab setzen                  (siehe 7.4)
```

Auth **vor** Tabs, damit die wiederhergestellten Tabs bereits eingeloggt
laden. Genau so macht es die vizron-Vorlage
(`_authentication_state_manager.restore()` vor dem Tab-Restore), und das ist
der ganze Punkt der Übung.

### 7.1 Teil-Mounts

- `state.authentication` leer (keine Cookies, keine Origins) → Schritte 1–2
  überspringen, Cookies **nicht** löschen.
- `state.tabs` leer → Schritte 3–4 überspringen, vorhandene Tabs unangetastet
  lassen.

Damit ist "nur Auth aufspielen" ein normaler `PUT` mit leerem `tabs` und
braucht keinen eigenen Endpoint.

### 7.2 Auth aufspielen

```python
await client.storage.clear_cookies()
await client.storage.set_cookies(cookies=[...])  # ein Aufruf, alle Cookies
```

`Storage.setCookies` nimmt die ganze Liste auf einmal — kein
`Network.setCookie`-pro-Cookie mit `asyncio.gather` wie in der Vorlage, und
kein "Chromium rejected cookie X"-Rauschen pro Cookie. `CookieParam` bekommt
`name`, `value`, `domain`, `path`, `secure`, `http_only`, `same_site` und
`expires` (nur wenn gesetzt); `url` bleibt leer, `domain`/`path` reichen.

localStorage pro Origin, nacheinander:

1. `client.target.create_target(url=origin, background=True)`
2. `client.target.attach_to_target(target_id, flatten=True)`
3. `session.dom_storage.enable()`, dann
   `session.dom_storage.clear(storage_id=...)` und pro Item
   `session.dom_storage.set_dom_storage_item(storage_id=..., key=..., value=...)`
4. `client.target.close_target(target_id=...)`

**Warum ein Hintergrund-Tab und nicht das Init-Script der Vorlage:** der
Ansatz `addScriptToEvaluateOnNewDocument` + `evaluate` auf dem fokussierten Tab
schreibt nur dann etwas, wenn dieser Tab zufällig schon auf der richtigen
Origin steht — beim Mount auf einen frischen Browser praktisch nie. Außerdem
entfernt die browsertunnel-Vorlage das Init-Script nie wieder, es ruft also bei
*jedem* späteren Load erneut `localStorage.clear()` auf. Das ist ein echter
Bug und wird nicht übernommen. Über `DOMStorage` gibt es zudem keinen
String-Bau mit `json.dumps` und keine Quoting-Risiken.

Origins nacheinander, nicht parallel: es sind wenige, und ein frischer Browser
soll nicht 20 Tabs gleichzeitig laden.

### 7.3 Tabs herstellen

Vorhandene Page-Targets ermitteln (`get_targets()`), dann:

- Sind mehr Targets offen als `state.tabs` lang ist, werden die überzähligen
  mit `close_target` geschlossen.
- Sind weniger offen, werden die fehlenden mit
  `create_target(url="about:blank", background=True)` angelegt.
- Bestehende Targets werden **wiederverwendet** statt geschlossen und neu
  angelegt — so wie in vizron. Grund: ein Browser ohne offenes Fenster kann
  sich beenden, und Target-Churn ist beim Screencast sichtbar.

Für jeden Tab dann, parallel über alle Tabs (`asyncio.gather`):

1. `attach_to_target(target_id, flatten=True)` → Session, `page.enable()`.
2. Restore-Script installieren:
   `session.page.add_script_to_evaluate_on_new_document(source=...)` →
   `identifier` merken.
3. Load-Listener starten: `session.listen(PageEvent.LOAD_EVENT_FIRED,
   LoadEventFiredEvent, timeout=settings.browser_state_restore_timeout)` als
   Task, **bevor** navigiert wird.
4. `session.page.navigate(url=tab.url, transition_type="address_bar")`;
   `navigation.error_text` → dieser Tab gilt als fehlgeschlagen.
5. Auf den Load-Task warten. Timeout → `warning` loggen und weitermachen, den
   Mount nicht abbrechen (Vorlage macht es genauso).
6. Im `finally`: Task canceln falls noch offen und Script mit
   `remove_script_to_evaluate_on_new_document(identifier=...)` entfernen.
   Dieser Schritt ist nicht optional — ohne ihn bleibt das Script für die
   Lebensdauer des Tabs aktiv.

Das Restore-Script (aus vizron übernommen, an unser Modell angepasst):

```js
(() => {
    if (window.location.origin !== <origin>) return;
    try {
        window.sessionStorage.clear();
        <setItem-Zeilen>
    } catch (_) {}

    const restoreScroll = () => window.requestAnimationFrame(
        () => window.requestAnimationFrame(
            () => window.scrollTo(<x>, <y>),
        ),
    );
    if (document.readyState === "complete") {
        restoreScroll();
    } else {
        window.addEventListener("load", restoreScroll, {once: true});
    }
})();
```

Alle eingesetzten Werte über `json.dumps`, auch die Origin. Der
Origin-Vergleich verhindert, dass eine Weiterleitung fremden sessionStorage
beschreibt. Der doppelte `requestAnimationFrame` ist Absicht: erst nach dem
zweiten Frame steht das Layout, vorher verpufft `scrollTo`.

Warum sessionStorage hier per Script und nicht per `DOMStorage` wie
localStorage: sessionStorage hängt am Tab, nicht an der Origin — `StorageId`
kann ihn nicht eindeutig adressieren. Das Init-Script ist der Weg, und weil es
sauber wieder entfernt wird, ist es hier auch unproblematisch.

### 7.4 Aktiven Tab setzen

`client.target.activate_target(target_id=...)`, danach auf der Session des
Tabs `page.bring_to_front()`. Fehler dabei werden geloggt, nicht geworfen.

### 7.5 Fehlerbehandlung

Die Vorlagen schlucken alles in `except Exception: logger.debug(...)`. Hier:
Fehler pro Tab und pro Origin sammeln und

- wenn **gar nichts** hergestellt werden konnte (kein Cookie gesetzt, kein Tab
  navigiert): `BrowserStateFailedException` → 503;
- bei Teilerfolgen: `warning` mit Origin bzw. Tab-Index und Fehlertyp,
  **niemals** mit Werten (siehe 10), und der Mount gilt als erfolgreich.

Der Grund für "Teilerfolg ist Erfolg": ein einzelner Tab, dessen Seite nicht
mehr erreichbar ist, darf einen sonst korrekt aufgespielten Login nicht
entwerten.

## 8. Settings und Validierung

### 8.1 Neue Settings (`BrowserWorkerSettings`)

```python
browser_state_restore_timeout: float = Field(default=10, gt=0)
browser_state_max_tabs: int = Field(default=20, gt=0)
```

`browser_state_max_tabs` begrenzt, wie viele Tabs ein Mount öffnen darf — ein
Body mit 5000 Tabs soll den Worker nicht lahmlegen. Überschreitung →
`BrowserStateInvalidException`.

### 8.2 Validierung vor dem Mount

- Jede `tab.url` muss Schema `http` oder `https` haben. Alles andere
  (`file:`, `chrome:`, `javascript:`, `data:`) wird abgelehnt →
  `BrowserStateInvalidException` (422). Das ist die einzige Sicherheitsprüfung
  auf URLs im Browser Worker, siehe 9.
- `0 <= active_tab_index < len(tabs)`, sofern `tabs` nicht leer ist.
- `len(tabs) <= browser_state_max_tabs`.
- Jede `origin` im Auth-State muss `scheme://netloc` mit `http`/`https` sein.

## 9. Bewusst nicht übernommen

| Aus der Vorlage | Entscheidung |
| --- | --- |
| `SecurityPolicy.is_url_allowed` | Keine Allowlist im Browser Worker. Der Worker führt aus, was das Control Plane ihm sagt; Policy gehört ins Control Plane. Es bleibt die Schema-Prüfung aus 8.2. |
| `EventBus` / `visualize=False` | Der Browser Worker hat keinen Event-Bus für Navigation; der Screencast sieht die Änderungen ohnehin. |
| `BrowserTabs`-Registry mit Session-Cache | Der Browser Worker hält keinen Tab-Zustand. Targets werden pro Operation frisch über `get_targets()` ermittelt, Sessions pro Operation attached und wieder detached. Zustand, den niemand invalidiert, geht sonst irgendwann schief. |
| `root_target_id`-Sonderfall | Entfällt, weil wir am Browser-Endpoint hängen (siehe 0). |
| `_restored`-Guard | Entfällt, `PUT` darf beliebig oft laufen. |
| `Network.setCookie` pro Cookie | Ersetzt durch ein `Storage.setCookies`. |
| Init-Script für localStorage, das nie entfernt wird | Ersetzt durch `DOMStorage` in einem Hintergrund-Tab. |
| `FocusedTabClient` | Es gibt keinen fokussierten Tab im Browser Worker; alle Operationen sind browserweit. |

## 10. Sicherheit

Der Payload enthält gültige Session-Cookies und Tokens aus dem Storage. Also:

- Keine Cookie-Werte, localStorage- oder sessionStorage-Werte in Logs, auch
  nicht auf `debug`. Geloggt werden nur Cookie-**Namen**, Origins, Tab-Indizes
  und Fehlertypen.
- Kein Schreiben auf Platte im Browser Worker. Der State existiert nur in der
  Response.
- Kein Caching der Response (`Cache-Control: no-store` auf dem GET).
- Der Browser-Worker-Port ist nicht öffentlich. Beim späteren Durchreichen über
  das Control Plane muss der Endpoint an das Lease gebunden sein, sonst liest
  ein fremder Aufrufer fremde Logins aus.

## 11. Anbindung nach außen

1. `browser_worker/app.py`: `browser_state_router` in `ROUTERS`, die neuen Specs in
   `API_ERRORS`, `BrowserStateProvider()` in den Container.
2. `scripts/export_openapi_schemas.py` und `scripts/generate_http_clients.sh`
   laufen lassen → `generated/browser_worker` bekommt `capture_browser_state` /
   `mount_browser_state`, das Frontend die TS-Pendants.
3. Control Plane: ein `browser_state`-Feature, das über den generierten Client
   an den Worker des Leases durchreicht
   (`GET`/`PUT /api/v1/browsers/{id}/state`). **Folgeschritt** — er braucht die
   Entscheidung, wo der State persistiert wird. Das Browser Worker speichert
   bewusst nichts.

## 12. Tests

Gemäß `AGENTS.md` nur das Nötigste: `browser_worker/tests/test_browser_state.py`
mit einem Fake-`BrowserStateStore` und drei Fällen:

1. Roundtrip: `GET` serialisiert Playwright-förmig, `PUT` desselben Bodys
   kommt unverändert am Port an.
2. `PUT` mit `active_tab_index=3` bei zwei Tabs → 422.
3. `PUT` mit `tab.url = "file:///etc/passwd"` → 422.

Die CDP-Infrastruktur bleibt ungetestet, wie `ChromeScreenRecorder` auch.

## 13. Umsetzungsreihenfolge

1. `application/models.py`, `ports.py`, `exceptions.py`
2. `presentation/schemas.py` + `mapper.py` (Casing-Übersetzung), `errors.py`
3. `service.py` inkl. `_validate`, `provider.py`, `router.py`, `app.py`
   verdrahten — ab hier ist die API mit einem Fake-Store lauffähig
4. Die drei Tests aus 12
5. `infrastructure/scripts.py` (Capture-Expression, Restore-Script-Builder)
6. `infrastructure/cdp_state.py`: erst Cookies, dann localStorage, dann
   Tab-Capture, zuletzt Tab-Restore
7. Settings ergänzen
8. Codegen neu erzeugen
