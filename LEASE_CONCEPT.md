# Browser-Lease-Konzept

Status: Zielbild mit implementierter Basis. Die offenen Härtungsschritte sind in
Abschnitt 17 ausdrücklich abgegrenzt.

## 1. Entscheidung in Kurzform

Für Browserplane soll eine aktive Browser-Session nicht mehr eine einmalig
vergebene TTL besitzen, sondern eine erneuerbare Lease:

- Heartbeat-/Renew-Intervall: **10 Sekunden**
- Lease-TTL: **30 Sekunden**
- Grace Period: **45 Sekunden**
- Reaper-Intervall: **5 Sekunden**
- maximale absolute Sessiondauer: zunächst **nicht erzwingen**, aber im Modell
  vorsehen

```text
letzter erfolgreicher Renew
0 s             10 s            20 s            30 s                  75 s
|----------------|---------------|---------------|----------------------|
ACTIVE           heartbeat       heartbeat       GRACE                  RECLAIMING
                                                    kein neuer Holder      hard cleanup
                                                    alte Lease erneuerbar  keine Rückkehr
```

Die entscheidende Semantik ist:

1. Bis `expires_at` ist die Lease `ACTIVE` und darf Browseroperationen
   ausführen.
2. Zwischen `expires_at` und `reclaim_after` ist sie in `GRACE`. Der Browser
   bleibt exklusiv für diese Lease reserviert und darf noch mit derselben
   Lease-Identität reaktiviert werden. Neue Browserkommandos werden erst nach
   einem erfolgreichen Renew wieder angenommen.
3. Sobald der Reaper atomar nach `RECLAIMING` wechselt, ist eine Erneuerung
   endgültig ausgeschlossen. Der Worker wird hart bereinigt und neu
   provisioniert.
4. Ein Browser wird erst nach erfolgreichem Cleanup und Readiness-Check wieder
   `READY`. Ablauf allein macht ihn niemals wieder verfügbar.

Postgres ist die autoritative Control-Plane-Wahrheit. Der Browser Worker ist
für den tatsächlichen Runtime-Zustand verantwortlich. Eine lokale
`asyncio.Lock` darf nur lokale Abläufe serialisieren, aber niemals die
clusterweite Exklusivität einer Lease begründen.

## 2. Warum der heutige Stand dafür nicht ausreicht

Im Repository gibt es bereits eine gute Grundlage:

- `leases` werden seit Migration `0009_create_leases.py` in Postgres
  persistiert;
- ein Browser besitzt die logischen Zustände `READY`, `LEASED`, `STOPPING`,
  `STOPPED` und `FAILED`;
- `SqlBrowserRepository.find_available()` nutzt bereits
  `FOR UPDATE SKIP LOCKED`;
- der neue Worker-Endpunkt `POST /api/v1/release` bündelt Browser-, Recording-,
  Download-, Screencast- und Workspace-Cleanup;
- das Frontend kennt Session-Reconnect, explizites Close und getrennte Tunnel-
  und Screencast-Verbindungen.

Die heutige Lease ist trotzdem noch keine robuste erneuerbare Lease:

- `ttl_seconds` wird nur bei Open/Resume gesetzt. Es gibt keinen Renew.
- Abgelaufene Leases werden nur bei `create()`, `get()` oder `list()` lazy
  entdeckt. Wenn alle Browser `LEASED` sind, scheitert die Browserauswahl in
  `SessionService._pick_available_browser()` bereits vor `LeaseService.create()`;
  der Expiry-Pfad wird dann gerade bei erschöpftem Pool nicht erreicht.
- `LeaseService._lock` schützt nur ein Python-Objekt innerhalb eines
  Backend-Prozesses. Der Service ist request-scoped; mehrere Requests und
  Backend-Instanzen teilen dieses Lock nicht.
- Browserauswahl, Browserstatus und Lease-Erzeugung sind kein gemeinsamer
  atomarer Datenbankvorgang.
- Eine Lease wird heute gelöscht. Damit fehlen Verlauf, Release-Grund,
  Cleanup-Status und eine belastbare Wiederaufnahme nach einem Crash.
- `BrowserService.release()` setzt den Slot nur von `LEASED` auf `READY`.
  Der neue Worker-Release-Pfad wird vom Lease-Lifecycle noch nicht benutzt.
- Ein bereits aufgebauter Tunnel kennt keine Lease-Generation. Er könnte nach
  einem DB-Ablauf weiter auf einer alten CDP-Verbindung arbeiten, bis diese
  aktiv geschlossen wird.
- Die Backend-Startup-Logik setzt die bekannten Slots wieder auf `READY`, ohne
  zuerst alte Leases und den tatsächlichen Worker-Zustand zu reconciliieren.

Damit sind zwei Wahrheiten voneinander getrennt: „Wer darf den Browser
benutzen?“ in der Control Plane und „welcher Chromium-Prozess läuft wirklich?“
in der Data Plane. Das Lease-Konzept muss beide über einen wiederholbaren
Reclaim-Ablauf zusammenführen.

## 3. Begriffe und Invarianten

### Lease, Session und Browser-Slot

- **Session-ID** ist die stabile, frontendseitige Identität. Im aktuellen
  Modell ist sie identisch mit der Lease-ID. Das kann zunächst so bleiben.
- **Lease** ist der zeitlich begrenzte, exklusive Nutzungsanspruch einer
  Session auf genau einen Browser-Slot.
- **Browser-Slot** ist die stabile ID und Worker-Zuordnung in Postgres.
- **Runtime** ist der konkrete Chromium-Prozess samt Profil, CDP-Verbindungen,
  Screencast, Downloads und Recordings. Sie ist wegwerfbar.
- **Generation** (Fencing Token) ist eine pro Browser monoton steigende Zahl.
  Eine neue Vergabe bekommt immer eine höhere Generation als jede frühere
  Vergabe desselben Slots.

Folgende Invarianten dürfen nie verletzt werden:

1. Pro Browser gibt es höchstens eine nicht terminale Lease.
2. Ein Browser in `READY` hat keine nicht terminale Lease und enthält eine
   frisch geprüfte, saubere Runtime.
3. Ein Browser mit `ACTIVE`, `GRACE` oder `RECLAIMING` Lease ist niemals
   auswählbar.
4. Nur `(lease_id, browser_id, generation)` in der aktuell autorisierten
   Kombination darf neue Operationen ausführen.
5. Ein altes Kommando darf nach Reclaim oder Neuvergabe keine Wirkung auf die
   neue Runtime haben.
6. Ein fehlgeschlagenes oder unbekanntes Cleanup führt zu `FAILED`/Quarantäne,
   niemals zu `READY`.
7. Jeder Zustandsübergang ist idempotent oder durch einen Compare-and-set
   geschützt.

## 4. Zustandsmodelle

### Lease-Zustand

```text
                 renew
              +---------+
              |         v
CREATING --> ACTIVE --> GRACE --> RECLAIMING --> RELEASED
               |          ^           |
               | renew    |           +--------> FAILED_CLEANUP
               +----------+                         |
                                                    +--> RECLAIMING (retry)

ACTIVE -- explicit close/suspend/failure --> RECLAIMING
GRACE  -- explicit close                  --> RECLAIMING
```

- `CREATING`: DB-Zuordnung ist reserviert, aber die Worker-Runtime wird noch
  vorbereitet. Sie ist nicht an den Client auszugeben.
- `ACTIVE`: Renew ist erlaubt; Nutzung ist erlaubt.
- `GRACE`: gleiche Lease hält den Slot weiter exklusiv; Renew ist noch erlaubt;
  Nutzung erst wieder nach erfolgreichem Renew.
- `RECLAIMING`: terminale Fence-Grenze. Renew und Attach sind verboten.
- `RELEASED`: Cleanup und neue Readiness waren erfolgreich.
- `FAILED_CLEANUP`: Slot bleibt quarantänisiert; ein Recovery-Loop versucht
  den Reclaim erneut.

`GRACE` muss nicht zwingend bei exakt `expires_at` in die Datenbank geschrieben
werden. Es darf als abgeleiteter Zustand gelten: `state = ACTIVE` und
`expires_at <= db_now < reclaim_after`. Der irreversible Wechsel nach
`RECLAIMING` muss dagegen persistiert und atomar sein.

### Browser-Zustand

```text
STARTING -> READY -> LEASED -> RECYCLING -> READY
    |         |         |          |
    +---------+---------+----------+--> FAILED --> STARTING
```

`RECYCLING` sollte als neuer Browserstatus ergänzt werden. `STOPPING` beschreibt
eher einen administrativ beendeten Slot; ein normaler Lease-Reclaim ist ein
Recycle. `READY` ist eine starke Zusage: sauberer Browser, erreichbares CDP,
keine aktive Lease.

## 5. Persistenzmodell

Die bestehende Lease-Tabelle sollte erweitert, nicht bei Ablauf gelöscht
werden. Vorgeschlagene Felder:

```text
leases
  id                    uuid primary key       # Session-ID
  browser_id            uuid not null
  owner_id              uuid not null
  generation            bigint not null
  state                 varchar not null
  created_at             timestamptz not null
  activated_at           timestamptz null
  last_renewed_at        timestamptz null
  expires_at             timestamptz not null
  reclaim_after          timestamptz not null
  reclaim_started_at     timestamptz null
  released_at            timestamptz null
  release_reason         varchar null
  cleanup_attempts       integer not null default 0
  cleanup_retry_at       timestamptz null
  cleanup_error_code     varchar null           # keine sensitiven Details

browsers
  ...
  state                 varchar not null
  generation            bigint not null default 0
  active_lease_id       uuid null
```

Empfohlene Constraints:

- Foreign Key `leases.browser_id -> browsers.id`;
- `UNIQUE (browser_id)` für nicht terminale Lease-Zustände als partieller
  Unique Index;
- `UNIQUE (browser_id, generation)`;
- `browsers.active_lease_id` referenziert die Lease oder ist `NULL`;
- Checks für `expires_at > last_renewed_at` und
  `reclaim_after >= expires_at`;
- Index auf `(state, reclaim_after)` und `(state, cleanup_retry_at)` für den
  Reaper.

Browserstatus und `active_lease_id` sind bewusst gemeinsam gespeichert. So
kann die Datenbank die zentrale Zuordnung prüfen, statt sie nur aus zwei
unabhängigen Tabellenzeilen zu erraten.

Zeitvergleiche und neue Deadlines sollen aus der Datenbankzeit stammen. Alle
Lease-Entscheidungen innerhalb eines SQL-Statements verwenden dieselbe
Zeitbasis; die Uhren verschiedener Backend-Container sind dann für die
Korrektheit irrelevant. API-Antworten geben zusätzlich `server_time` zurück,
damit Clients nur Countdown-Anzeigen berechnen und niemals selbst über Ablauf
entscheiden.

## 6. Atomare Vergabe

`SessionService.open()` darf nicht länger zuerst einen Browser lesen und ihn
später in einem anderen Service reservieren. Eine Repository-Operation
`allocate_lease(...)` übernimmt den gesamten Control-Plane-Teil in einer
Transaktion:

1. Einen `READY`-Browser mit `FOR UPDATE SKIP LOCKED` auswählen.
2. Browserzeile sperren und nochmals prüfen, dass `active_lease_id IS NULL` ist.
3. `generation = generation + 1` setzen.
4. Browser auf `LEASED` und `active_lease_id = session_id` setzen.
5. Lease in `CREATING` mit derselben Generation anlegen.
6. Commit.

Danach wird ohne offene DB-Transaktion die Data Plane vorbereitet. Externe
HTTP-/CDP-Aufrufe dürfen niemals innerhalb der Row-Lock-Transaktion liegen.

1. Worker für den Slot mit der erwarteten Generation claimen bzw. eine frisch
   bereitgestellte Runtime verifizieren.
2. Downloads und sonstigen Restzustand bereinigen.
3. Optionalen Authentication-/Browser-State mounten.
4. CDP-Readiness prüfen.
5. Lease per Compare-and-set von `CREATING` nach `ACTIVE` setzen und Deadlines
   aus DB-Zeit berechnen.
6. Erst jetzt Session und Zugangspfade zurückgeben.

Schlägt die Vorbereitung fehl, geht dieselbe Lease nach `RECLAIMING`; der
zentrale Cleanup-Pfad übernimmt. Der Slot wird nicht durch ein einfaches
Status-Update freigegeben.

Das vermeidet auch den heutigen Kapazitäts-Deadlock: Vor der Auswahl kann der
Request-Pfad einen kurzen fälligen Reaper-Durchlauf anstoßen. Er wartet nicht
auf langes Cleanup, aber bereits erfolgreich recycelte Browser werden sofort
sichtbar. Der Hintergrund-Reaper bleibt die primäre Instanz.

## 7. Renew und Heartbeats

### Eine einzige Renew-Semantik

Der Application-Service bietet genau eine Operation:

```text
renew(lease_id, generation, holder_credential) -> lease_deadlines
```

Die SQL-Operation ist ein bedingtes Update:

```text
UPDATE leases
SET last_renewed_at = db_now,
    expires_at      = db_now + 30 seconds,
    reclaim_after   = db_now + 75 seconds
WHERE id            = :lease_id
  AND generation    = :generation
  AND state         = 'active'
  AND db_now        < reclaim_after
RETURNING ...
```

Damit ist Renew idempotent, konkurrierende Heartbeats sind harmlos und ein
Reaper gewinnt eindeutig: Hat er zuerst `RECLAIMING` gesetzt, kann kein Renew
die Lease wiederbeleben. Hat Renew zuerst aktualisiert, ist sie nicht mehr
fällig und der Reaper überspringt sie.

Ein Renew während der abgeleiteten Grace Period setzt die Lease wieder auf
volle 30 Sekunden. Nach `reclaim_after` oder ab `RECLAIMING` ist eine Rückkehr
ausgeschlossen.

### Wer sendet den Heartbeat?

Für den Browser-UI-Pfad ist der **Control-WebSocket-Tunnel** die kanonische
Lebensverbindung, nicht der Screencast. Der Gateway-Handler startet nach einem
autorisierten Attach einen Lease-Keeper, der alle 10 Sekunden dieselbe
`renew()`-Operation aufruft, solange die Tunnelverbindung nachweislich lebt.
Transport-Ping/Pong und ein enger Timeout müssen halb offene Verbindungen
erkennen. Wenn Handler oder Backend-Prozess stirbt, enden die Renews
automatisch.

Das ist zuverlässiger als ausschließlich `setInterval()` im Angular-Tab:
Hintergrundtabs, eingefrorene Seiten und Sleep können JavaScript-Timer stark
verzögern. Der Client muss die Lease trotzdem beobachten und bei einem
abgelehnten Renew/Tunnel-Close den Browser als verloren behandeln.

Für Agenten ohne dauerhaften Tunnel gibt es zusätzlich einen expliziten
HTTP-Endpoint:

```text
POST /api/v1/sessions/{session_id}/lease/renew
```

Er verwendet exakt denselben Use Case. Normale Browseraktivität wie Maus-,
CDP- oder Screencast-Traffic verlängert die Lease nicht implizit. Dadurch ist
die Liveness-Semantik beobachtbar und ein bloß hängender Datenstrom hält keine
Ressource fest.

Eine erfolgreiche Antwort enthält mindestens:

```json
{
  "session_id": "...",
  "generation": 12,
  "server_time": "...",
  "expires_at": "...",
  "reclaim_after": "...",
  "next_renew_in_seconds": 10
}
```

Der Client verwendet exponentiellen Backoff nur innerhalb des 10-Sekunden-
Takts, zum Beispiel sofort, nach 1 Sekunde und nach 3 Sekunden. Er darf keine
Retry-Schleife über `reclaim_after` hinaus fortsetzen.

### Holder-Credential

`owner_id` wird derzeit vom Client frei geliefert und ist keine
Autorisierung. Mindestens für Renew, Attach, Release und Suspend braucht die
Lease deshalb ein zufälliges Holder-Credential oder später echte
Benutzerauthentifizierung. Ein Lease-Secret wird nur einmal zurückgegeben und
nur gehasht gespeichert. Es gehört nicht in Logs oder normale URL-Querys.

Das Credential schützt gegen fremdes Verlängern; die Generation schützt gegen
alte, ehemals legitime Holder. Beide lösen unterschiedliche Probleme.

## 8. Enforcement und Fencing an der Plane-Grenze

Nur die Datenbank zu aktualisieren reicht nicht: Ein bereits verbundener
Gateway-Prozess kann eine alte CDP-Verbindung besitzen. Deshalb gibt es zwei
Schutzebenen.

### Gateway als erster Enforcement Point

Beim Tunnel-Handshake validiert das Backend Lease-ID, Credential, Generation
und aktuellen Zustand. Der Handler bindet diese Werte unveränderlich an die
Verbindung. Er beendet Tunnel und Screencast, wenn:

- Renew endgültig abgelehnt wird;
- die Lease nach `RECLAIMING` wechselt;
- die Browser-Generation nicht mehr übereinstimmt;
- administrativer Drain oder explizites Close beginnt.

Zusätzlich soll der Reaper ein lokales Connection-Registry-Signal auslösen,
damit Verbindungen derselben Backend-Instanz sofort schließen. Diese Registry
ist nur eine Optimierung; Korrektheit darf nicht davon abhängen, weil der
Reaper auf einer anderen Instanz laufen kann.

### Data Plane als endgültige Fence-Grenze

Der Worker muss die aktuelle Browser-Generation kennen. Claim, Release und
andere lebenszyklusverändernde Worker-Aufrufe tragen
`(browser_id, generation)`. Der Worker akzeptiert keine kleinere oder fremde
Generation.

Da der aktuelle Worker den CDP-WebSocket direkt für einen Browser freigibt,
ist ein einmal ausgegebener CDP-Stream nicht pro Kommando fencebar. Daher gilt
für Hard Reclaim zwingend:

1. Runtime aus der Worker-Registry entfernen, sodass kein neuer Attach an die
   alte Runtime möglich ist.
2. Alle Screencasts, Recordings, Downloads und CDP-Verbindungen beenden.
3. Den alten Chromium-Prozess vollständig stoppen.
4. Workspace und Browserprofil entfernen.
5. Einen neuen Chromium-Prozess mit derselben stabilen Slot-ID, aber neuer
   Generation starten.

Der Prozesswechsel ist damit das harte Fence: selbst ein alter Gateway kann
auf der geschlossenen CDP-Verbindung keine Kommandos mehr ausführen. Eine
Runtime darf aus Isolationsgründen nie nur durch Zurücksetzen des Postgres-
Status an den nächsten Holder weitergegeben werden.

## 9. Reaper und Hard Reclaim

Im Backend-Lifespan läuft ein periodischer Reaper. Alle fünf Sekunden holt er
eine kleine Batch fälliger Leases:

```text
state = ACTIVE AND reclaim_after <= db_now
OR state = FAILED_CLEANUP AND cleanup_retry_at <= db_now
```

Die Auswahl erfolgt mit `FOR UPDATE SKIP LOCKED`. Dadurch können mehrere
Backend-Instanzen Reaper ausführen, ohne globale Leader Election und ohne
dasselbe Objekt gleichzeitig zu bearbeiten.

Für neue fällige Leases geschieht in einer kurzen Transaktion:

1. Lease sperren und Deadline nochmals prüfen.
2. Lease per CAS auf `RECLAIMING` setzen.
3. Browser per CAS auf `RECYCLING` setzen.
4. `reclaim_started_at`, Release-Grund und Attempt erfassen.
5. Commit.

Danach läuft das externe Cleanup:

1. Lokale Tunnel schließen, soweit vorhanden.
2. `POST /api/v1/release` am zugeordneten Worker mit Browser-ID und Generation
   aufrufen. Der neue Worker-Release-Service ist dafür der richtige zentrale
   Einstiegspunkt.
3. Release-Erfolg durch Worker-State und Prozess-/CDP-Zustand verifizieren.
4. Eine frische Runtime für den Slot starten.
5. Readiness und Browser-ID/Generation prüfen.
6. In einer neuen Transaktion Lease `RELEASED`, Browser `READY` und
   `active_lease_id = NULL` setzen.

Schlägt ein Schritt fehl:

- Lease wird `FAILED_CLEANUP`;
- Browser wird `FAILED`;
- `cleanup_attempts` und `cleanup_retry_at` werden mit begrenztem Backoff
  aktualisiert, beispielsweise 1 s, 2 s, 5 s, 10 s, danach 30 s;
- der Slot bleibt aus der Vergabe ausgeschlossen;
- ein Alarm wird nach mehreren Fehlern ausgelöst.

Der Release-Endpunkt und jeder Cleanup-Schritt müssen idempotent sein. „Kein
Browser läuft“ und „Verzeichnis existiert nicht“ sind beim Release Erfolge.
Ein Prozesscrash zwischen zwei Schritten wird vom nächsten Reaper-Lauf
fortgesetzt.

Damit ein in `RECLAIMING` abgestürzter Reaper nicht dauerhaft hängt, werden
auch alte `RECLAIMING`-Datensätze nach einer Ownership-Timeout erneut
übernommen. Das ist eine Arbeits-Ownership des Cleanup-Jobs und nicht die
Browser-Lease selbst.

## 10. Explizites Close, Suspend und Verbindungsabbruch

- `DELETE /sessions/{id}` ist idempotent. Unbekannt oder bereits released
  bedeutet Erfolg. Es überspringt die Grace Period und startet sofort den
  Reclaim.
- Fehlgeschlagenes Open/Resume/State-Mounting benutzt denselben Reclaim-Pfad.
- `suspend()` captured und persistiert Authentication-/Browser-State zuerst.
  Erst nach erfolgreicher Persistenz startet der Reclaim. Der Suspend-Response
  darf erst erfolgreich sein, wenn der Browser sicher nicht mehr nutzbar ist;
  der vollständige Recycle kann asynchron fertig werden.
- Ein einzelner WebSocket-Disconnect löst **kein** sofortiges Release aus.
  Er stoppt nur die automatischen Renews. Damit überlebt die Session Reloads
  und kurze Netzausfälle bis zum Ende der Grace Period.
- Der Screencast ist nicht leaseführend. Sein Disconnect darf die Session
  nicht freigeben; sein Weiterlaufen darf sie nicht verlängern.
- Ein Browser-/CDP-Crash startet sofort Reclaim mit Ursache `runtime_failed`,
  ohne TTL oder Grace abzuwarten.

## 11. Startup, Shutdown und Reconciliation

### Backend-Start

`BrowserService.start()` darf die Slot-Tabelle nicht pauschal auf `READY`
zurücksetzen. Vor Readiness des Backends läuft eine Reconciliation:

1. Konfigurierte Slot-IDs mit den DB-Zeilen abgleichen.
2. Nicht terminale Leases und Browserstatus zusammen prüfen.
3. Überfällige Leases nach `RECLAIMING` übernehmen.
4. Für `CREATING`, `RECYCLING`, `FAILED` oder widersprüchliche Zustände ein
   idempotentes Cleanup/Provisioning anstoßen.
5. Aktive, noch gültige Leases nicht stillschweigend löschen. Entweder die
   Runtime samt Generation ist verifizierbar und die Session darf weiterleben,
   oder sie wird sauber gereclaimt.
6. Nur verifizierte, leasefreie Runtime-Slots als `READY` markieren.

Das Backend kann `/health` bereits beantworten, bleibt aber `/readiness = 503`,
bis Reconciliation abgeschlossen oder zumindest der verwaltbare Poolzustand
bekannt ist.

### Backend-Shutdown

Beim normalen Drain werden keine Leases pauschal released: In einer
mehrinstanzigen Control Plane kann ein anderer Gateway/Reaper übernehmen.
Die Instanz stoppt neue Handshakes, beendet ihre Lease-Keeper und schließt
lokale Tunnel. Nur ein ausdrücklich gewünschter kompletter System-Shutdown
deprovisioniert alle Worker.

## 12. API- und Fehlersicht

Die vorhandenen Session-Responses sollten für aktive Sessions mindestens
`generation`, `expires_at` und `reclaim_after` enthalten. Das Frontend kann
damit `active`, `reconnecting/grace` und `lost` darstellen.

Empfohlene fachliche Fehler, ohne die exakten HTTP-Codes jetzt festzuschreiben:

- `LEASE_NOT_FOUND`: nie vorhanden oder History nicht mehr sichtbar;
- `LEASE_CREDENTIAL_INVALID`: Holder nicht autorisiert;
- `LEASE_EXPIRED`: in Grace, Nutzung braucht erfolgreichen Renew;
- `LEASE_RECLAIMING`: irreversible Bereinigung hat begonnen;
- `LEASE_FENCED`: Generation ist veraltet;
- `BROWSER_RECYCLING`: Slot ist noch nicht wieder bereit.

Das Projekt ist noch in Entwicklung; die Spec legt deshalb Semantik und
Zustandsübergänge fest, nicht unnötig früh jeden Statuscode oder Payload bis ins
letzte Feld.

## 13. Observability und Betriebsgrenzen

Strukturierte Logs tragen `lease_id`, `browser_id`, `generation`, Zustand,
Release-Grund und Cleanup-Attempt. Credentials, Worker-Geheimnisse, CDP-URLs,
Cookies und gespeicherter Browser-State werden nie geloggt.

Mindestens folgende Metriken sind sinnvoll:

- Browser pro Zustand (`ready`, `leased`, `recycling`, `failed`);
- Leases pro effektivem Zustand (`active`, `grace`, `reclaiming`, failed);
- Renew-Erfolge/-Fehler und Renew-Latenz;
- Zeit vom letzten Renew bis Reclaim;
- Cleanup-Dauer, Retry-Anzahl und Fehlergrund;
- Zahl aktiv geschlossener Tunnel beim Fence;
- `no_browser_available` getrennt nach echter Belegung, Recycling und Failure;
- Abweichungen zwischen DB- und Worker-Generation.

Sinnvolle Alerts:

- Slot länger als zwei Minuten in `RECYCLING` oder `FAILED`;
- Lease länger als zwei Reaper-Intervalle über `reclaim_after`, ohne
  `RECLAIMING` zu erreichen;
- wiederholte Generation-Mismatches;
- dauerhaft hohe Grace-Quote, weil das auf zu aggressive Timings oder
  instabile Verbindungen hinweist.

Die Werte 10/30/45 sind Startwerte, keine Naturkonstanten. Nach Einführung
sollten p95/p99 von Renew-Latenz, kurze Disconnects, Cleanup-Dauer und
Grace-Recoveries beobachtet werden. Erst diese Messwerte rechtfertigen eine
Änderung.

## 14. Fehlerfälle, die das Design abdecken muss

| Fehler | Erwartetes Verhalten |
| --- | --- |
| Frontend-Tab wird neu geladen | Renews stoppen kurz; Attach mit derselben Lease ist bis `reclaim_after` möglich. |
| Clientprozess stirbt | Kein Renew; nach 30 s Grace, nach 75 s harter Reclaim. |
| Einzelner Heartbeat geht verloren | Zwei weitere 10-s-Fenster bleiben vor Expiry. |
| Backend-Instanz stirbt | Ihre Renews stoppen; DB-Deadline bleibt autoritativ; anderer Reaper reclaimt. |
| Reaper stirbt nach DB-Transition | Lease bleibt `RECLAIMING`; Recovery übernimmt idempotent. |
| Worker ist nicht erreichbar | Slot bleibt `FAILED`, wird nicht neu vergeben; Cleanup-Retry. |
| Renew und Reaper laufen gleichzeitig | DB-CAS entscheidet eindeutig; keine Wiederbelebung aus `RECLAIMING`. |
| Alter Tunnel sendet nach Neuvergabe | Generation wird abgelehnt; alte Runtime/CDP-Verbindung wurde beendet. |
| Explizites Close wird doppelt gesendet | Beide Requests enden fachlich erfolgreich; nur ein Cleanup läuft. |
| Cleanup gelingt teilweise | Kein `READY`; weitere Attempts setzen beim erreichten Zustand fort. |
| DB ist während Renew kurz weg | Client/Gateway retryt innerhalb TTL; ohne Erfolg greift die sichere Expiry. |

## 15. Umsetzungsreihenfolge

### Phase 1: korrekter Reclaim-Pfad

- Worker-`POST /release` fertigstellen und idempotent machen.
- `RECYCLING` ergänzen.
- Einen zentralen `release_and_recycle()`-Use-Case bauen.
- Explizites Close, Open-/Resume-Fehler und Runtime-Crash darauf routen.
- Browser erst nach Worker-Release, neuer Provisionierung und Readiness auf
  `READY` setzen.

Ohne diese Phase wäre eine kurze Lease gefährlich, weil Ressourcen zwar
logisch frei, aber physisch nicht sauber wären.

### Phase 2: persistente Zustandsmaschine und atomare Vergabe

- Lease-/Browser-Schema um Zustand, Deadlines, Generation und Cleanup-Felder
  erweitern.
- `allocate_lease()` als eine DB-Transaktion implementieren.
- Delete-on-expiry entfernen; History terminal aufbewahren und später per
  Retention-Job löschen.
- Request-scoped `asyncio.Lock` aus der Korrektheitslogik entfernen.

### Phase 3: Reaper und Reconciliation

- Lifespan-Reaper mit `SKIP LOCKED`, Batches und Recovery bauen.
- Startup-Reconciliation einführen.
- lokale Tunnel-Registry zum schnellen Schließen anbinden.
- Worker-Generation und Readiness verifizieren.

### Phase 4: Renew

- gemeinsamen Renew-Use-Case und HTTP-Endpoint ergänzen.
- Lease-Keeper an den Control-WebSocket binden.
- Frontendzustände für Grace, Reconnect und endgültigen Verlust ergänzen.
- Default-`ttl_seconds=300` und Frontend-`SESSION_TTL_SECONDS=600` nach der
  Migration durch serverseitig konfigurierte 30 Sekunden ersetzen. Clients
  sollen die Sicherheitsgrenzen nicht frei auf bis zu 86.400 Sekunden setzen.

### Phase 5: Fencing härten

- Generation auf Worker-Claim/Release und Lifecycle-Aufrufe propagieren.
- stale Generation im Worker ablehnen.
- garantieren, dass Hard Reclaim alle alten CDP-/Screencast-Verbindungen
  beendet und eine neue Runtime erzeugt.

## 16. Schlanke Validierung

Gemäß `AGENTS.md` reichen wenige Lifecycle-Smoke-Szenarien; die sich noch
entwickelnde API soll nicht mit einer großen Vertragstestsuite eingefroren
werden:

1. Heartbeat alle 10 Sekunden hält eine Session über mehrere TTLs aktiv.
2. Ohne Heartbeat ist sie nach 30 Sekunden in Grace und nach spätestens
   Reaper-Intervall plus 75 Sekunden im Reclaim.
3. Reconnect in Grace reaktiviert dieselbe Lease und Generation; nach Beginn
   von `RECLAIMING` ist das unmöglich.
4. Zwei parallele Open-Requests erhalten niemals denselben Browser.
5. Ein alter Tunnel kann nach Reclaim/Neuvergabe keine Aktion auf der neuen
   Runtime ausführen.
6. Nach Worker-Release sind Chromium-Prozess, Recording/Screencast, Downloads
   und Workspace weg; erst der frische, CDP-bereite Prozess macht den Slot
   `READY`.
7. Backend- oder Reaper-Crash mitten im Cleanup heilt nach Neustart aus dem
   persistierten Zustand.

Zusätzlich genügen bestehende Tests, Linting, Typprüfung und ein direkter
Startup-/Import-Smoke-Test.

## 17. Bewusste Entscheidungen und offene Punkte

Für die erste Implementierung sind folgende Entscheidungen getroffen:

- Postgres bleibt Lease-Koordinator; kein Redis/etcd zusätzlich.
- Jede Browser-Lease ist exklusiv.
- Grace reserviert den Browser weiter und erlaubt Recovery derselben Lease.
- Hard Reclaim ist irreversibel und erzeugt eine frische Runtime.
- Die Generation ist pro Browser monoton.
- Nur der Control-Tunnel führt die UI-Lease; Screencast und gewöhnlicher
  Browsertraffic tun es nicht.
- Release ist idempotent und überspringt Grace.
- Timings sind serverseitige Konfiguration, nicht frei wählbarer Clientinput.

Vor Implementierung noch explizit abzustimmen:

1. Soll eine Session in Grace wirklich reaktivierbar sein? Diese Spec sagt
   **ja**. Falls nein, wäre die Grace nur Cleanup-Verzögerung und würde ohne
   Nutzen Kapazität blockieren.
2. Soll ein erfolgreicher Suspend bereits nach sicherem Fencing oder erst nach
   vollständig frischem `READY`-Browser antworten? Empfehlung: nach sicherem
   Fencing und persistiertem State; Recycling darf im Hintergrund enden.
3. Wie wird das Holder-Credential transportiert, solange das Projekt noch keine
   echte Authentifizierung hat? Empfehlung: einmaliges Lease-Secret für HTTP
   und ein kurzlebiges Attach-Ticket für den WebSocket, nicht als langlebiger
   Query-Parameter.

## 18. Definition of Done

Das Lease-Feature ist architektonisch fertig, wenn nicht nur eine Deadline
abläuft, sondern folgende Aussage auch bei konkurrierenden Requests und
Prozesscrashes stimmt:

> Nach dem letzten erfolgreichen Renew darf die bisherige Session höchstens bis
> zum Ende der Grace Period wiederbelebt werden. Danach kann sie die alte oder
> eine neue Browser-Runtime nicht mehr beeinflussen. Der Slot wird nur nach
> nachgewiesenem vollständigem Cleanup und erfolgreicher Neu-Provisionierung
> erneut vergeben.

Genau diese Garantie ist die Grenze zwischen einer einfachen TTL-Spalte und
einer belastbaren Lease zwischen Control Plane und Data Plane.
