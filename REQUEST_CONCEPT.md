# Browser-Request-Konzept

Status: Entwurf und Scope für eine spätere Implementierung.

Diese Spec beschreibt das gewünschte Verhalten und die Architekturgrenzen. Sie
legt bewusst keine vollständige Klassenstruktur, SQL-Statements oder
Nebenläufigkeitsimplementierung fest.

## Ziel

Wenn kein Browser verfügbar ist, soll der Aufrufer mit einem normalen
asynchronen Aufruf warten können:

```python
lease = await control_plane.acquire_browser(
    owner_id=owner_id,
    timeout=60,
)
```

Der Aufrufer soll weder `try_acquire()` wiederholen noch selbst pollen.
`await` parkt nur die Coroutine; dabei wird kein Thread beschäftigt.

Die Control Plane verwaltet wartende Requests persistent. Lokale
`asyncio.Future`-Objekte dienen nur dazu, wartende Coroutines im jeweiligen
API-Prozess wieder aufzuwecken.

## Aktuelle Problemstellung

Besonders störend ist momentan der unmittelbare fachliche Start im
FastAPI-Lifespan:

```python
container = app.state.dishka_container
lifecycle = await container.get(Lifecycle)
async with container(scope=Scope.REQUEST) as scoped:
    browsers = await scoped.get(BrowserService)
    await browsers.start()
    sessions = await scoped.get(SessionService)
    await sessions.reap_expired()
```

`await browsers.start()` startet beim Hochfahren der API direkt auf beiden
konfigurierten Browser Workern eine Browser-Runtime. `reap_expired()` führt
zusätzlich einen fachlichen Scheduler-Schritt aus. Damit besitzt der
API-Prozess bereits beim Booten Pool- und Lease-Verantwortung, obwohl noch kein
Browser angefordert wurde.

Diese Kopplung ist Teil des Problems, das dieses Konzept lösen soll:

- Der Start einer API-Instanz darf keine Browser-Nachfrage simulieren.
- Mehrere API-Instanzen dürfen die gleichen Browser-Runtimes nicht jeweils neu
  starten oder dieselbe Reaper-Arbeit anstoßen.
- API-Readiness soll nicht vom unmittelbaren Start aller Browser-Runtimes
  abhängen.
- Slot-Reconciliation, bedarfsgesteuerte Provisionierung und Lease-Reaping
  gehören zum Scheduler-Lifecycle.
- Der FastAPI-Lifespan soll nur API-nahe Infrastruktur öffnen und schließen.

Der unmittelbare `BrowserService.start()`-Aufruf und der direkte Reaper-Lauf
sollen daher aus `backend/src/backend/lifespan.py` verschwinden. Beim Start des
Schedulers werden vorhandene Slots und persistente Zustände reconciliiert;
Browser-Runtimes entstehen erst durch echte Nachfrage.

## Entscheidungen

- Postgres ist die Source of Truth für Requests, Browser und Leases.
- Ein Notification-Mechanismus beschleunigt Wakeups, entscheidet aber nie über
  den fachlichen Zustand.
- Die erste Notification-Implementierung verwendet Postgres
  `LISTEN/NOTIFY`.
- Notification wird als kleine Infrastrukturprimitive abstrahiert und nicht
  als Domain-EventBus modelliert.
- Es gibt zunächst keine Priorität und keine Browser-Requirements.
- Wartende Requests werden nach `created_at, id` als FIFO behandelt.
- Während des Wartens bleibt keine normale DB-Transaktion oder
  Query-Verbindung offen.
- Browser-Runtimes werden bei Bedarf provisioniert. Der Start des API-Backends
  startet nicht automatisch beide konfigurierten Browser.
- Dispatcher und Lease-Reaper sollen nicht als lose Tasks direkt im
  FastAPI-Lifespan implementiert werden.

## Persistentes Request-Modell

Der erste Entwurf benötigt:

```text
browser_requests
  id
  owner_id
  test_run_id nullable
  status
  created_at
  expires_at
  lease_id nullable
```

`owner_id` ist die fachliche Besitzidentität. `test_run_id` ist optionale
Korrelation für einen Testlauf. Eine vom Client erzeugte `id` darf zur
idempotenten Wiederaufnahme verwendet werden.

Statuswerte:

```text
QUEUED
PROVISIONING
ASSIGNED
CANCELLED
EXPIRED
```

- `QUEUED`: Der Request wartet auf Kapazität.
- `PROVISIONING`: Für den Request wird eine Browser-Runtime vorbereitet.
- `ASSIGNED`: Eine Lease wurde committed und ist über `lease_id` verknüpft.
- `CANCELLED`: Der Aufrufer hat den Request beendet.
- `EXPIRED`: Die Deadline wurde überschritten.

`ASSIGNED`, `CANCELLED` und `EXPIRED` sind terminal. Die weitere
Lebensdauer einer erfolgreichen Zuweisung gehört dem Lease-Modell aus
`LEASE_CONCEPT.md`.

Zusätzliche technische Spalten, Constraints und Indizes darf die
Implementierung ergänzen, soweit sie die beschriebenen Zustände und
Invarianten unterstützen.

## Notification-Abstraktion

Die Publish-Seite soll klein und infrastrukturell bleiben:

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class Notification:
    channel: str
    payload: str


class Notifier(ABC):
    @abstractmethod
    async def notify(self, notification: Notification) -> None: ...
```

Daneben gibt es einen getrennten langlebigen Listener. Seine genaue API bleibt
der Implementierung überlassen. Er muss Notifications empfangen und an lokale
Waiter beziehungsweise den Dispatcher weiterreichen können.

Die Postgres-Implementierung lebt ausschließlich in `infrastructure`:

- `Notifier` veröffentlicht über `pg_notify`;
- der Listener hält eine eigene langlebige `LISTEN`-Verbindung;
- Kanalnamen und Payload-Encoding bleiben Implementierungsdetails dieses
  Adapters;
- normale Queries verwenden weiterhin kurzlebige Verbindungen aus dem Pool.

Application- und Domain-Code dürfen weder `asyncpg`, `LISTEN`,
`pg_notify` noch konkrete Postgres-Kanalnamen kennen.

Notifications bedeuten nur: „Der persistente Zustand könnte sich geändert
haben.“ Nach jedem Wakeup wird der Request neu aus dem Repository gelesen.
Verlorene, doppelte oder zusammengefasste Notifications müssen unschädlich
sein. Ein langsamer Recovery-Scan stellt Fortschritt nach verlorenen
Notifications und Prozessneustarts sicher.

## Acquire-Ablauf

```text
Request persistent anlegen
          |
          v
sofortige atomare Vergabe versuchen
          |
     +----+----+
     |         |
  möglich   nicht möglich
     |         |
     v         v
 ASSIGNED    QUEUED
     |         |
     |         v
     |      Future registrieren
     |         |
     |      await Wakeup
     |         |
     +----> Zustand erneut lesen
               |
        ASSIGNED / terminal / weiter warten
```

Das Future transportiert nicht die autoritative Lease, sondern nur das Wakeup.
Die Lease wird nach `ASSIGNED` aus der Datenbank gelesen.

Beim Registrieren eines Waiters muss das Race zwischen Registrierung und
Zustandsänderung berücksichtigt werden. Eine mögliche Lösung ist: Future
registrieren, danach den DB-Zustand lesen und anschließend warten. Die konkrete
Synchronisation bleibt der Implementierung überlassen.

Timeout, Cancellation und Assignment müssen atomar gegeneinander entschieden
werden. Das Ergebnis darf entweder eine sichtbare Lease oder ein terminaler
Request sein, niemals eine unauffindbare Zuweisung.

## Datenbankgrenzen

Die aktuelle request-scoped `AsyncSession` committet erst am Ende eines
HTTP-Requests. Sie darf deshalb nicht über einen möglicherweise 15 Minuten
wartenden Acquire gehalten werden.

Benötigt werden kurze, eigenständige Transaktionen für:

- Request anlegen oder idempotent laden;
- Request und Browser claimen;
- Lease erzeugen und Request auf `ASSIGNED` setzen;
- Status nach einem Wakeup lesen;
- Timeout oder Cancellation speichern.

Zwischen diesen Operationen werden Session, Transaktion und normale
Pool-Verbindung freigegeben. Externe Aufrufe an Browser Worker erfolgen
ebenfalls außerhalb einer DB-Transaktion.

Die konkrete Form kann eine Session-Factory, Unit of Work oder ein anderer
kleiner Transaction Runner sein.

## Dispatcher

Der Dispatcher wird bei neuen Requests und neuer Browser-Kapazität über den
Notifier geweckt. Zusätzlich führt er einen langsamen Recovery-Scan aus.

Er soll:

1. den ältesten gültigen `QUEUED`-Request claimen;
2. einen freien Browser-Slot exklusiv reservieren;
3. bei Bedarf die Runtime außerhalb der DB-Transaktion provisionieren;
4. Lease und `ASSIGNED`-Status atomar persistieren;
5. den wartenden API-Prozess benachrichtigen.

Mehrere Dispatcher dürfen langfristig parallel laufen können. Row Locks,
Compare-and-set-Updates und Datenbank-Constraints müssen Doppelvergabe
verhindern. Die genaue SQL- und Locking-Strategie ist Teil der Implementierung.

## API

Der normale Pfad bleibt die vorhandene Route:

```text
POST /api/v1/sessions
```

Sie wartet intern auf `acquire_browser()` und antwortet erst nach erfolgreicher
Zuweisung. Timeout und optionale Request-ID werden über das Request-Schema oder
eine gleichwertige API-Konvention transportiert.

Optionale Recovery-/Betriebsrouten:

```text
GET    /api/v1/browser-requests/{request_id}
DELETE /api/v1/browser-requests/{request_id}
```

Sie sind nicht Teil des normalen Acquire-Flows. `GET` unterstützt
Wiederaufnahme und Diagnose. `DELETE` storniert nur einen noch wartenden
Request; eine bereits zugewiesene Lease wird über den bestehenden
Session-/Lease-Release-Pfad beendet.

## Browser-Provisionierung und Lifespan

Heute ruft `backend/src/backend/lifespan.py` beim API-Start
`BrowserService.start()` auf. Dieser Service startet auf beiden statisch
konfigurierten Browser Workern unmittelbar eine Browser-Runtime. Zusätzlich
startet der Lifespan den Lease-Reaper mit `asyncio.create_task()`.

Das Zielbild trennt diese Verantwortungen:

```text
API-Prozess
  HTTP/WebSocket
  lokaler Future-Registry
  langlebiger Notification-Listener

Scheduler-Prozess
  Request-Dispatcher
  Lease-Reaper
  Slot-/Runtime-Reconciliation
  Recovery-Scans

Browser Worker
  startet und bereinigt Chromium auf Anforderung
```

Der API-Lifespan startet nur API-nahe Infrastruktur wie den Listener und
behandelt Readiness und Shutdown. Er startet keine Browser-Runtimes, keinen
Dispatcher und keinen Lease-Reaper.

Ein separater Scheduler-Einstiegspunkt ist das bevorzugte Ziel. Er kann dasselbe
Backend-Image und denselben Dependency-Container verwenden. Seine
Hintergrundschleifen sollen gemeinsam überwacht und sauber beendet werden.

Beim Scheduler-Start werden konfigurierte Slots nur registriert oder
reconciliiert. Chromium wird erst bei Nachfrage gestartet. Ob später ein
konfigurierbarer Warm-Pool hinzukommt, bleibt außerhalb dieses ersten Scopes.

## Vorgesehene Module

Die genauen Klassennamen darf die Implementierung an die vorhandene Architektur
anpassen. Der fachliche Scope liegt ungefähr hier:

```text
backend/src/backend/features/browser_requests/
  domain/
  application/
  infrastructure/
    repository.py
    notifier.py
    postgres_notifier.py
    listener.py
  presentation/
  feature.py

backend/src/backend/scheduler.py
backend/src/backend/control_plane/
```

Anbindungen an bestehende Module:

- `features/sessions`: wartendes Acquire statt sofortigem
  `NoBrowserAvailableException`;
- `features/leases`: atomare Lease-Erzeugung und Notification bei frei
  gewordener Kapazität;
- `features/browsers`: Slot-Registrierung vom Start einer Runtime trennen;
- `infrastructure/database`: kurze Transaktionen für den wartenden Use Case;
- `lifespan.py`: fachliche Worker entfernen;
- `compose.yml`: separaten Scheduler-Prozess ergänzen.

## Fehler- und Recovery-Verhalten

- Stirbt ein API-Prozess, verschwindet sein Future; der Request bleibt
  persistent.
- Stirbt der Scheduler, verarbeitet sein Nachfolger `QUEUED` und
  `PROVISIONING` weiter.
- Verliert der Listener seine Verbindung, verbindet er sich neu und stößt eine
  Zustandsprüfung der lokalen Waiter an.
- Geht eine Notification verloren, findet der Recovery-Scan die Arbeit.
- Endet die Provisionierung nach Cancellation oder Timeout, darf daraus keine
  Lease für den terminalen Request entstehen.
- Der Start mehrerer API-Instanzen darf weder Browser-Runtimes mehrfach starten
  noch zusätzliche Dispatcher erzeugen.

## Nicht Teil dieses Scopes

- Prioritäten;
- unterschiedliche Browser-Requirements oder Capability-Matching;
- garantierte Event-Zustellung oder ein allgemeiner EventBus;
- eine breite neue API-Vertragstestsuite;
- automatische Skalierung der Browser-Worker-Container;
- Festlegung aller Klassen, SQL-Statements und HTTP-Statuscodes.

## Schlanke Validierung

Gemäß `AGENTS.md` genügen wenige Smoke-Szenarien:

1. Ein Acquire wartet ohne Kapazität und erhält nach Freigabe genau eine Lease.
2. Während des Wartens bleibt keine normale DB-Verbindung belegt.
3. Timeout gegen Assignment endet eindeutig mit Lease oder terminalem Request.
4. Ein verlorenes Notify oder ein Scheduler-Neustart verliert keinen
   persistenten Request.
5. Parallele Dispatcher vergeben Request und Browser nicht doppelt.
6. Der API-Start startet keine der zwei Browser-Runtimes.

## Definition of Done

Ein Aufrufer kann mit einem einzigen `await` bis zu seiner Deadline auf einen
Browser warten. Postgres enthält den rekonstruierbaren Request-Zustand. Futures
und Notifications beschleunigen nur das Aufwecken. Keine DB-Transaktion bleibt
während des Wartens offen, und die Vergabe erzeugt atomar höchstens eine Lease.

Der API-Prozess besitzt keine fachlichen Scheduler-Aufgaben und startet keine
Browser-Runtime. Browser werden durch Nachfrage über den separaten Scheduler
provisioniert.
