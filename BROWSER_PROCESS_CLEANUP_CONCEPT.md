# Konzept: zuverlässige Freigabe und Bereinigung von Browsern

## Ausgangslage

Der Backend-Healthcheck kann erfolgreich sein, während `POST /api/v1/sessions`
mit `503 no_browser_available` antwortet. Das bedeutet zunächst nur, dass das
Backend keinen Browser mit dem logischen Zustand `READY` findet. Es beweist
nicht, dass tatsächlich noch funktionierende Chromium-Prozesse laufen.

Im aktuellen Aufbau gibt es zwei feste Browser-Slots. Jeder Browser Worker
hält genau einen Chromium-Prozess. Das Backend verwaltet dazu die Zustände
`READY`, `LEASED` und `FAILED` in Postgres und die zugehörigen Leases nur im
Arbeitsspeicher.

Die beobachtete Störung hat daher zwei verschiedene Cleanup-Ebenen:

1. **Logisches Cleanup:** Eine abgelaufene oder verwaiste Lease muss entfernt
   und ihr Slot wieder freigegeben werden.
2. **Physisches Cleanup:** Der alte Chromium-Prozess samt Kindprozessen und
   temporärem Profil muss beendet und für die nächste Session frisch gestartet
   werden.

Beide Ebenen müssen funktionieren. Nur einen Prozess zu beenden oder nur einen
Datenbankstatus auf `READY` zu setzen reicht nicht aus.

## Konkrete Schwachstellen im aktuellen Code

### 1. Lease-Ablauf kann den Pool dauerhaft blockieren

`SessionService.open()` ruft zuerst `_pick_available_browser()` auf. Erst wenn
ein Browser gefunden wurde, ruft es `LeaseService.create()` auf.

Die Bereinigung abgelaufener Leases (`LeaseService._expire()`) wird jedoch erst
innerhalb von `LeaseService.create()` oder `LeaseService.get()` ausgeführt.
Wenn alle Browser in Postgres noch als `LEASED` markiert sind, findet
`_pick_available_browser()` keinen Slot und `create()` wird nie erreicht. Damit
werden die abgelaufenen Leases in genau der Situation nicht bereinigt, in der
die Kapazität benötigt wird. Wiederholte Requests liefern dann weiterhin 503.

Das ist nach Sichtung des Codes die wahrscheinlichste unmittelbare Ursache des
beschriebenen Verhaltens.

### 2. Eine Session-Freigabe recycelt Chromium nicht

`LeaseService.release()` ruft derzeit nur `BrowserService.release()` auf. Das
setzt den Datenbankstatus von `LEASED` auf `READY`. Der Browser-Worker-Browser wird
dabei weder geschlossen noch zurückgesetzt.

Damit können zwischen zwei Sessions unter anderem Tabs, Cookies, Cache,
Service Worker, Downloads, Renderer-Prozesse und defekte CDP-Zustände erhalten
bleiben. Das ist sowohl ein Stabilitäts- als auch ein Isolationsproblem.

### 3. Prozessbeendigung zielt nur auf den Chromium-Hauptprozess

`ChromeProcess.stop()` sendet zuerst `terminate()` und nach fünf Sekunden
`kill()` an den gestarteten Prozess. Chromium verwendet aber mehrere
Kindprozesse. Bei Abstürzen oder hartem Abbruch ist nicht garantiert, dass alle
Renderer-, GPU- und Utility-Prozesse mit beendet und zeitnah eingesammelt
werden.

Im Container läuft außerdem kein expliziter Init-/Reaper-Prozess. Ohne
`init: true` beziehungsweise `tini` können verwaiste Zombie-Kindprozesse länger
bestehen bleiben.

### 4. Healthchecks prüfen nicht die Browser-Funktionsfähigkeit

Die Browser-Worker-Endpunkte `/health` und `/readiness` liefern aktuell immer `OK`.
Sie prüfen weder, ob Chromium lebt, noch ob der CDP-Endpunkt antwortet. Ein
Worker kann deshalb für Docker und Backend gesund aussehen, obwohl sein Browser
abgestürzt oder unbenutzbar ist.

### 5. Leases sind nur pro Backend-Prozess bekannt

Der `InMemoryLeaseStore` verliert alle Leases bei einem Backend-Neustart und ist
bei mehreren Backend-Prozessen nicht gemeinsam nutzbar. Die Browserzustände
liegen hingegen in Postgres. Dadurch können beide Wahrheiten auseinanderlaufen:
Postgres sagt `LEASED`, während kein Backend-Prozess mehr die Lease kennt.

### 6. Gleichzeitige Session-Eröffnung ist nicht vollständig atomar

Das Finden eines freien Slots und dessen Reservierung sind getrennte Schritte.
Die lokale `asyncio.Lock` schützt nur einen Backend-Prozess. Für mehrere
Requests, Prozesse oder Instanzen sollte die Reservierung in einer einzigen
Datenbanktransaktion erfolgen, zum Beispiel über
`SELECT ... FOR UPDATE SKIP LOCKED` plus Zustandsänderung und Lease-Erzeugung.

## Zielbild

Ein Browser-Slot durchläuft folgenden Lebenszyklus:

```text
STARTING -> READY -> LEASED -> RECYCLING -> READY
     |          |       |          |
     +----------+-------+----------+-> FAILED -> STARTING
```

- `READY` bedeutet nicht nur „kein Lease-Eintrag“, sondern „Chromium und CDP
  wurden erfolgreich geprüft und der Browser ist sauber“.
- Jede Lease hat eine persistierte Ablaufzeit und optional einen Heartbeat.
- Ablauf, explizites `DELETE`, fehlgeschlagenes Mounting und Browserabsturz
  führen über denselben idempotenten Release-/Recycle-Pfad.
- Ein Slot wird erst nach einem erfolgreichen Neustart und Readiness-Probe
  wieder `READY`.
- Cleanup darf beliebig oft aufgerufen werden und bleibt auch nach einem
  Teilausfall sicher.

## Empfohlene Lösung

### Priorität 0: akuten 503-Deadlock beseitigen

Vor jeder Suche nach einem verfügbaren Browser müssen abgelaufene Leases
bereinigt werden. Dafür sollte `LeaseService` eine öffentliche Methode wie
`expire_due_leases()` erhalten. Der Open-/Resume-Ablauf wird dann:

1. Fällige Leases ermitteln und freigeben beziehungsweise recyceln.
2. Einen verfügbaren Browser atomar reservieren.
3. Erst danach State mounten und die Session zurückgeben.

Zusätzlich sollte ein kleiner Hintergrund-Reaper in festen Abständen, etwa alle
5 bis 15 Sekunden, abgelaufene Leases bereinigen. Der Request-Pfad bleibt
trotzdem notwendig; der Reaper allein bietet wegen Zeitfenstern und möglichen
Task-Ausfällen keine ausreichende Garantie.

Als minimaler Hotfix kann die bestehende `_expire()`-Logik vor
`_pick_available_browser()` aufgerufen werden. Die saubere Lösung ist jedoch
eine atomare Allocate-Operation, damit Expiry und Reservierung nicht über
mehrere lose Serviceschritte verteilt bleiben.

### Priorität 1: Browser bei jeder Freigabe recyceln

Eine Session-Freigabe sollte nicht direkt von `LEASED` nach `READY` wechseln.
Stattdessen:

1. Slot auf `RECYCLING` setzen, sodass er nicht neu vergeben werden kann.
2. Aktive Proxies, Screencasts und Recordings für diesen Browser schließen.
3. Im Browser Worker `DELETE /browser` ausführen.
4. Verifizieren, dass der alte Prozess beendet ist.
5. Temporäres Profil entfernen.
6. Im Browser Worker mit derselben stabilen Slot-ID einen neuen Browser erstellen.
7. CDP mit einer kurzen Probe testen.
8. Erst dann den Slot auf `READY` setzen.

Schlägt ein Schritt fehl, bleibt der Slot `FAILED`; ein Recovery-Worker versucht
mit begrenztem Backoff erneut, ihn neu zu provisionieren. Er darf nicht trotz
fehlgeschlagenem Cleanup als `READY` angeboten werden.

Alle Release-Ursachen verwenden diesen einen Ablauf:

- explizites `DELETE /sessions/{id}`;
- TTL-Ablauf;
- fehlgeschlagenes Open/Resume/State-Mounting;
- festgestellter Chromium- oder CDP-Absturz;
- administrativer Drain beziehungsweise Shutdown.

### Priorität 1: robuste Prozessbaum-Beendigung

Der Browser Worker sollte Chromium in einer eigenen Prozessgruppe starten.

- Unter Linux: neue Session/Prozessgruppe (`start_new_session=True`) und beim
  Stoppen zuerst `SIGTERM`, danach mit Timeout `SIGKILL` an die gesamte Gruppe.
- Unter Windows bei lokaler Entwicklung: Job Object oder ersatzweise eine
  explizite Prozessbaum-Beendigung verwenden.
- Nach jedem Signal immer auf den Hauptprozess warten, damit kein Zombie bleibt.
- Cleanup in `finally` ausführen und auch bei Cancellation mit einem begrenzten
  Timeout abschließen.
- Profil erst löschen, nachdem der komplette Prozessbaum beendet wurde.
- Die zu beendende PID, Prozessgruppe, Dauer und Eskalation strukturiert loggen.

Für die Compose-Services sollte zusätzlich `init: true` gesetzt werden. Docker
startet dann einen kleinen Init-Prozess, der Signale korrekt weitergibt und
verwaiste Kindprozesse einsammelt. Eine sinnvolle `stop_grace_period` muss etwas
größer als der interne Terminate-/Kill-Timeout sein.

### Priorität 1: Leases persistent und selbstheilend machen

Leases sollten in Postgres statt ausschließlich im Arbeitsspeicher liegen. Eine
Lease-Tabelle benötigt mindestens:

- `id`, `browser_id`, `owner_id`;
- `created_at`, `expires_at`;
- optional `last_heartbeat_at` und `release_reason`;
- eindeutige aktive Lease pro `browser_id`.

Beim Backend-Start läuft eine Reconciliation:

1. Abgelaufene Leases als freizugeben markieren.
2. Jeden konfigurierten Browser-Worker-Slot inspizieren.
3. Unbekannte oder nicht erreichbare Browser recyceln.
4. DB-Zustand und tatsächlichen Worker-Zustand angleichen.
5. Nur erfolgreich geprüfte Slots auf `READY` setzen.

Damit heilt ein Backend-Neustart verwaiste Zustände, statt sie nur durch ein
Upsert scheinbar zurückzusetzen.

### Priorität 2: aussagekräftige Readiness und Watchdog

`/health` sollte reine Prozess-Liveness bleiben. `/readiness` sollte dagegen
den Browser prüfen:

- existiert der erwartete Chromium-Prozess;
- ist er noch nicht beendet;
- antwortet der CDP-Endpunkt innerhalb eines kurzen Timeouts;
- stimmt die gemeldete Browser-ID mit dem Slot überein.

Ein Browser-Worker-Watchdog kann zusätzlich das Ende des Chromium-Prozesses
beobachten. Bei unerwartetem Exit setzt er den internen Zustand sofort zurück
und meldet den Slot als nicht bereit. Das Backend markiert ihn `FAILED` und
stößt Re-Provisioning an.

Der Docker-Healthcheck für den Browser Worker sollte `/readiness` statt `/health`
verwenden, sofern ein automatischer Container-Restart gewünscht ist. Dazu passt
eine Restart-Policy wie `restart: unless-stopped`. Der interne Recovery-Pfad
bleibt trotzdem nötig, damit nicht jeder Browserfehler den ganzen Container
neu starten muss.

### Priorität 2: Client-Lifecycle klar definieren

Der Client sollte bei einem normalen Schließen immer
`DELETE /sessions/{session_id}` senden. Ein WebSocket-Disconnect allein sollte
nicht sofort freigeben, weil kurzzeitige Netzunterbrechungen und State-Capture
weiter unterstützt werden sollen.

Für abgestürzte Clients begrenzt eine kurze Default-TTL den Schaden. Optional
kann eine aktive UI alle 30 Sekunden eine Lease verlängern. Fehlt der Heartbeat
für eine definierte Grace Period, übernimmt der Reaper. Eine maximale absolute
Sessiondauer verhindert dauerhaftes Festhalten durch fehlerhafte Clients.

## Idempotenz und Fehlerbehandlung

Der zentrale Vorgang `release_and_recycle(lease_id, reason)` sollte
idempotent sein:

- Eine bereits entfernte Lease gilt als erfolgreich freigegeben.
- `DELETE /browser` darf auch erfolgreich sein, wenn kein Browser existiert.
- Ein bereits laufender Recycle wird nicht doppelt gestartet.
- Ein neuer Browser wird nur für die erwartete Slot-ID akzeptiert.
- Erst eine erfolgreiche CDP-Probe erlaubt den Wechsel zu `READY`.

Der Zustand und die externe Aktion sollten über ein persistiertes
Reconciliation-Muster verbunden werden. Eine Datenbanktransaktion kann keinen
HTTP-Aufruf atomar einschließen; daher muss ein stehengebliebener Zustand wie
`RECYCLING` beim nächsten Reaper-Lauf wieder aufgenommen werden können.

## Observability

Mindestens folgende Metriken und strukturierte Logs sind sinnvoll:

- Anzahl Slots nach Zustand (`ready`, `leased`, `recycling`, `failed`);
- aktive und abgelaufene Leases;
- Session-Ablehnungen mit Grund;
- Alter der ältesten aktiven Lease;
- Chromium-Neustarts nach Ursache;
- Dauer und Fehler von Terminate, Kill, Profil-Cleanup und CDP-Probe;
- Chromium-Haupt-PID und optional Zahl der Kindprozesse;
- Reconciliation- und Reaper-Ergebnisse.

Bei `no_browser_available` sollte das Backend einmal kompakt den Poolzustand
loggen, beispielsweise beide Slot-Zustände, aktive Lease-IDs und deren
`expires_at`. Dadurch ist sofort sichtbar, ob echte Auslastung, verwaiste Leases
oder ausgefallene Worker vorliegen.

## Abgrenzung des 404 aus dem Log

`GET /api/v1/browser-state-snapshots` ist im aktuellen Router vorhanden. Ein
404 auf genau diesem Pfad deutet eher auf einen Versionsunterschied zwischen
laufendem Backend und Frontend, einen falschen Zielservice oder ein nicht neu
gebautes Image hin. Der 404 ist separat zu untersuchen und erklärt die
Browser-Erschöpfung nicht direkt.

## Vorgeschlagene Umsetzung in kleinen Schritten

### Schritt 1: sofortige Stabilisierung

- Expiry explizit vor der Browserauswahl ausführen.
- Einen periodischen Lease-Reaper im Backend-Lifespan starten und sauber
  canceln/abwarten.
- Bei 503 den vollständigen Pool-/Lease-Zustand loggen.
- `init: true`, eine Stop-Grace-Period und eine Restart-Policy für die
  Browser-Worker-Container ergänzen.

### Schritt 2: korrektes Session-Cleanup

- Zustand `RECYCLING` ergänzen.
- Zentralen idempotenten Release-/Recycle-Use-Case bauen.
- Browser-Worker-Browser bei Release wirklich destroyen und neu erstellen.
- Prozessgruppen-Cleanup und CDP-Readiness implementieren.

### Schritt 3: Crash Recovery

- LeaseStore nach Postgres migrieren.
- Allocate/Reserve transaktional machen.
- Startup-Reconciliation und Retry mit begrenztem Backoff ergänzen.
- Browser-Worker-Watchdog für unerwartete Chromium-Exits hinzufügen.

### Schritt 4: Betriebsreife

- Metriken und Alarmierung ergänzen.
- Heartbeat/Lease-Renewal nur dann ergänzen, wenn lange interaktive Sessions es
  benötigen.
- Grenzwerte anhand realer Laufzeiten einstellen.

## Schlanke Validierung

Entsprechend dem frühen Projektstadium genügen zunächst wenige Smoke-Szenarien:

1. Zwei Sessions belegen beide Slots; nach TTL kann ein neuer Open-Request ohne
   vorherigen GET erfolgreich einen Slot erhalten.
2. Nach `DELETE` hat der neue Browser eine andere PID, ein neues Profil und ist
   über CDP erreichbar.
3. Ein hart beendeter Chromium-Prozess wird erkannt; der Slot wird nicht als
   `READY` vergeben und anschließend automatisch wiederhergestellt.
4. Ein Backend-Neustart bei aktiven/verwaisten Leases reconciliert den Pool.
5. Nach wiederholtem Create/Delete bleiben weder Chromium-Kindprozesse noch
   temporäre `browser-worker-*`-Profile zurück.

Keine umfangreichen Payload- oder Statuscode-Vertragstests sind dafür nötig;
ein kleiner Lifecycle-Smoke-Test plus bestehende Lint-, Typ- und Startprüfungen
reicht für die erste Umsetzung.

## Entscheidungsempfehlung

Zuerst sollte der Expiry-before-allocation-Fehler behoben werden, weil er den
aktuellen dauerhaften 503-Zustand direkt erklärt. Unmittelbar danach sollte die
Freigabe zu einem echten Browser-Recycle erweitert werden. Persistente Leases
und Reconciliation machen das System anschließend robust gegen Prozess- und
Container-Neustarts.

Nur `pkill chromium` oder regelmäßige Container-Restarts einzubauen wäre keine
vollständige Lösung: Das beseitigt unter Umständen Prozesse, repariert aber
weder verwaiste Lease-Zustände noch garantiert es einen geprüften, isolierten
Browser vor der nächsten Vergabe.
