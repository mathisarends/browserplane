# Release eines Single-Browser-Workers

## Architekturentscheidung

Ein Browser-Worker besitzt höchstens genau einen Browser:

> **one worker = one browser**

Deshalb kennt der Worker keine `browser_id`. Sein eigener Endpunkt identifiziert
ihn bereits eindeutig. Eine zusätzliche Browser-ID im Request, in
`RunningBrowser` oder in einer Worker-Route wäre redundant und würde
fälschlicherweise ein Multi-Browser-Modell andeuten.

Die Verantwortlichkeiten sind getrennt:

| Ebene | Verantwortung |
| --- | --- |
| Backend | verwaltet `slot.id`, Worker-URL, Lease, Zustand und Generation |
| Worker | verwaltet seine einzige lokale Browser-Runtime |
| Chromium | ist ein wegwerfbarer Prozess dieses Workers |

Die `slot.id` bleibt im Backend sinnvoll. Sie wird dort für Datenbank,
Scheduling und Logs verwendet. Sie gehört aber nicht in die Worker-API.

## Aktuelle Worker-Routen

Die Worker-Routen adressieren eine singuläre Browser-Ressource und enthalten
keine Browser-ID:

| Funktion | Route |
| --- | --- |
| Browser starten | `POST /api/v1/browser` |
| Browser inspizieren | `GET /api/v1/browser` |
| CDP-Tunnel | `WS /api/v1/browser/cdp` |
| Screencast | `WS /api/v1/browser/screencast?mode=...` |
| Downloads auflisten | `GET /api/v1/browser/downloads` |
| Downloads löschen | `DELETE /api/v1/browser/downloads` |
| Download abrufen | `GET /api/v1/browser/downloads/{download_id}/file` |
| Recording starten | `POST /api/v1/browser/recordings` |
| Recording stoppen | `POST /api/v1/browser/recordings/{recording_id}/stop` |
| Recording abrufen | `GET /api/v1/browser/recordings/{recording_id}` |
| Recording-Datei | `GET /api/v1/browser/recordings/{recording_id}/file` |
| Browser-State | `GET/PUT /api/v1/browser/state` |
| Authentication-State | `GET/PUT /api/v1/browser/authentication-state` |
| Worker freigeben | `POST /api/v1/release` |

Der Release-Request enthält nur noch die Generation:

```json
{
  "generation": 12
}
```

Auch der Create-Request benötigt keine Browser-ID:

```json
{
  "generation": 12
}
```

Damit folgt auch der Release derselben Regel wie die übrigen geänderten Routen:
Der Request adressiert den Worker selbst und benötigt keine Browser-ID in Pfad
oder Payload.

## Lokales Worker-Modell

Der Worker benötigt nur die Generation und den lokalen CDP-Endpunkt:

```python
@dataclass(frozen=True, slots=True)
class RunningBrowser:
    generation: int
    upstream_cdp_url: str
```

Der Lifecycle ist:

```text
EMPTY
  |
  | create(generation)
  v
RUNNING(generation)
  |
  | release(generation)
  v
RELEASING(generation)
  |                     |
  | erfolgreich         | Fehler oder Timeout
  v                     v
EMPTY                 POISONED(generation)
                          |
                          | Worker neu starten/ersetzen
                          v
                        EMPTY
```

`POISONED` bedeutet: Der Prozess lebt eventuell noch, aber der Worker darf
keine neue Browser-Runtime annehmen. Das kann intern durch eine Release-Sperre
repräsentiert werden; eine öffentliche Enum ist dafür nicht zwingend nötig.

## Generation als Fencing-Token

Nach dem Entfernen der Browser-ID ist `generation` das Fencing-Token zwischen
Backend und Worker.

### `create(generation)`

- `EMPTY`: Browser für diese Generation starten.
- `RUNNING` mit derselben Generation: idempotenter Erfolg.
- `RUNNING` mit anderer Generation: Request ablehnen.
- `RELEASING` oder `POISONED`: Request ablehnen.

### `release(generation)`

- `RUNNING` mit derselben Generation: Release starten.
- `RELEASING` mit derselben Generation: dieselbe Release-Task abwarten.
- Generation wurde bereits freigegeben: idempotenter Erfolg.
- `RUNNING` mit anderer Generation: keine Mutation; Request als veraltet
  ablehnen.
- `POISONED` mit derselben Generation: Cleanup erneut versuchen oder
  Infrastruktur-Recovery auslösen.

Der Worker sollte die zuletzt akzeptierte Generation als High-Water-Mark
behalten. Andernfalls könnte ein verspäteter alter `create`-Request nach einem
erfolgreichen Release wieder eine alte Runtime starten.

Diese High-Water-Mark darf nicht mit dem Session-Workspace gelöscht werden. Soll
sie einen vollständigen Worker-Austausch überleben, muss sie außerhalb des
flüchtigen Worker-Dateisystems gespeichert oder beim Start mit der Control Plane
synchronisiert werden.

## Was bei einem Release-Fehler heute passiert

Der aktuelle `WorkerReleaseService` versucht nacheinander:

1. Recording zu schließen,
2. Download-Monitoring zu stoppen,
3. Screencast zu schließen,
4. Workspace zu löschen,
5. Chromium im `finally` des Browser-Scopes zu stoppen.

Exceptions werden gesammelt und abschließend als `ExceptionGroup` geworfen.
Das Backend setzt daraufhin Browser und Lease auf `FAILED`. Der Lease-Reaper
versucht den Cleanup später erneut.

```text
Browser: LEASED -> RECYCLING -> FAILED
Lease:   ACTIVE -> RECLAIMING -> FAILED
                                  |
                                  v
                              späterer Retry
```

Ein einmaliger Fehler hängt den Slot daher nicht zwingend dauerhaft fest. Es
bleiben aber vier wesentliche Risiken:

1. Ein Cleanup kann ohne Worker-seitigen Timeout unbegrenzt hängen.
2. Weitere Releases warten dann auf dem gehaltenen Lock.
3. Einige Services entfernen ihren Handle bereits vor einem erfolgreichen
   `close` oder `disconnect`; ein Retry kann die Ressource dann nicht mehr
   erreichen.
4. Nach beliebig vielen fehlgeschlagenen Retries gibt es keine harte Eskalation
   auf einen neuen Worker.

Der HTTP-Timeout des Backends löst diese Probleme nicht. Er beendet lediglich
das Warten des Backends, nicht nachweislich die bereits gestartete Operation im
Worker.

## Ziel für den Release

Ein Release muss zwei Eigenschaften verbinden:

1. **Isolation:** Keine Ressource der vorherigen Session ist für die nächste
   Session erreichbar.
2. **Fortschritt:** Ein defekter Cleanup blockiert den Cloud-Slot nicht
   unbegrenzt.

Ein Fehler darf nicht dadurch kaschiert werden, dass der Slot trotzdem als frei
markiert wird. Die Generation schützt vor veralteten API-Aufrufen, beendet aber
keinen offenen CDP-Socket und keinen hängenden Chromium- oder FFmpeg-Prozess.

Der sichere Ablauf lautet:

```text
release(generation)
        |
        v
Generation lokal prüfen
        |
        +-- veraltet/fremd --> ablehnen, keine Mutation
        |
        v
Browser aus dem öffentlichen Zugriff entfernen
create sperren
        |
        v
lokale Ressourcen mit festen Timeouts stoppen
        |
        v
Chromium-Prozessbaum immer stoppen
        |
        v
Workspace der alten Generation isolieren
        |
        v
Postconditions prüfen
        |
        +-- sauber --> Worker EMPTY
        |             Backend: Slot STOPPED, Lease RELEASED
        |
        +-- unsicher --> Worker POISONED
                        Backend: Slot und Lease FAILED
                                  |
                                  v
                           begrenzte Retries
                                  |
                                  v
                         Worker ersetzen/neustarten
```

## 1. Release als abgeschirmte Operation

Pro Generation darf nur eine Release-Task laufen. Zwei identische Requests
teilen dieselbe Operation. Ein HTTP-Disconnect darf die interne Release-Task
nicht abbrechen.

```python
async def release(self, generation: int) -> ReleaseResult:
    task = await self._get_or_start_release(generation)
    return await asyncio.shield(task)
```

Der Service muss selbst eine starke Referenz auf die Task halten.
`asyncio.shield` allein ist kein Zustandsmodell. Nach einem fehlgeschlagenen
Versuch darf ein neuer Request derselben Generation einen neuen Cleanup-Versuch
starten.

## 2. Jeder Cleanup erhält ein Zeitbudget

Jeder Schritt läuft unter einem eigenen `asyncio.timeout`. Unabhängige
Stop-Schritte können parallel laufen, damit sich die Timeouts nicht addieren.

| Schritt | Beispiel-Timeout | Für Wiedervergabe kritisch |
| --- | ---: | --- |
| Recorder schließen | 10 s | ja |
| Download-Monitor stoppen | 5 s | ja |
| Screencast stoppen | 5 s | ja |
| Chromium-Prozessbaum stoppen | 10 s | ja |
| aktiven Workspace isolieren | 5 s | ja |
| isolierte Dateien endgültig löschen | Hintergrundjob | nein |

Der Runner sammelt alle Fehler, ohne die übrigen Schritte nach der ersten
Exception abzubrechen:

```python
async def run_cleanup(
    name: str,
    timeout_seconds: float,
    action: Callable[[], Awaitable[None]],
) -> CleanupFailure | None:
    try:
        async with asyncio.timeout(timeout_seconds):
            await action()
    except Exception as error:
        return CleanupFailure(
            resource=name,
            error=error,
            timed_out=isinstance(error, TimeoutError),
        )
    return None
```

Chromium muss anschließend unabhängig von vorherigen Fehlern gestoppt werden.
Ein hängender Recording-Cleanup darf die wichtigste physische Fence nicht
verhindern.

Zusätzlich gilt ein Gesamtbudget für den Release. Dieses muss kleiner als der
HTTP-Timeout des Backends sein, beispielsweise 20 Sekunden im Worker und
25 Sekunden im Backend.

## 3. Cleanup-Handles retry-sicher verwalten

Eine Ressource darf erst nach erfolgreichem Cleanup vergessen werden.

Nicht retry-sicher:

```python
resource, self._resource = self._resource, None
await resource.close()
```

Retry-sicher:

```python
resource = self._resource
if resource is None:
    return

await resource.close()

if self._resource is resource:
    self._resource = None
```

Scheitert `close`, bleibt der Handle für den nächsten Versuch erhalten. Das
gilt insbesondere für Recording, Download-Client und Screencast. Alle
Cleanup-Methoden müssen idempotent sein: „bereits beendet“ oder „nicht
vorhanden“ ist ein erfolgreicher Zustand.

## 4. Workspace isolieren statt synchron vollständig löschen

Die nächste Session darf den alten Workspace nicht erreichen. Die physische
Löschung aller Dateien muss aber nicht im kritischen Release-Request erfolgen.

```text
runtime/<generation>/  ->  garbage/<release-id>/
```

Nach dem Stop aller Produzenten wird das Runtime-Verzeichnis atomar aus dem
aktiven Pfad verschoben. Die nächste Generation verwendet ein neues, leeres
Verzeichnis. Ein Hintergrundjob löscht isolierte Verzeichnisse später mit Retry.

- Schlägt die Isolation fehl, ist der Release fehlgeschlagen.
- Schlägt nur die spätere Löschung fehl, darf der Slot wieder verwendet werden.
- Alter und Größe des Garbage-Bereichs werden überwacht.

Damit blockiert ein langsames `shutil.rmtree` weder Event Loop noch Slot.

## 5. Erfolg über Postconditions definieren

Der Worker meldet Release-Erfolg nur, wenn:

- keine lokale Browser-Runtime mehr veröffentlicht ist,
- Chromium und seine Kindprozesse beendet sind,
- Recorder, Downloads und Screencast keine aktiven Prozesse, Tasks oder
  Verbindungen mehr besitzen,
- der Workspace der alten Generation isoliert ist,
- die Create-Sperre sicher aufgehoben werden kann.

Ist eine dieser Bedingungen nicht bewiesen, bleibt der Worker gesperrt. Eine
neue Browser-Runtime darf noch nicht gestartet werden.

## 6. Endliche Retries statt dauerhaftem `FAILED`

Temporäre Fehler werden mit exponentiellem Backoff und Jitter erneut versucht:

```text
5 s, 10 s, 20 s, 40 s, 60 s, 60 s, ...
```

Die lokale Recovery benötigt eine feste Grenze, beispielsweise:

- höchstens fünf Cleanup-Versuche oder
- höchstens zwei Minuten seit Beginn des Reclaims.

Nach dieser Grenze wird der Slot nicht optimistisch freigegeben. Stattdessen
wird der vollständige Worker neu gestartet oder ersetzt.

Das ist bei „one worker = one browser“ die sauberste Recovery: Mit der
Worker-Instanz verschwinden auch die einzige Browser-Runtime und unbekannte
In-Memory-Leaks.

## 7. Worker-Ersetzung sicher bestätigen

Der Health-Endpunkt sollte eine bei jedem Start neu erzeugte `instance_id`
liefern:

```json
{
  "status": "ready",
  "instance_id": "01J..."
}
```

Eine Ersetzung ist erst erfolgreich, wenn:

1. die alte Instanz nicht mehr verwendet wird,
2. der Endpunkt eine andere `instance_id` meldet,
3. der neue Worker `ready` ist,
4. Chromium verfügbar und der Workspace beschreibbar ist.

Erst dann setzt das Backend den Slot auf `STOPPED`, finalisiert die Lease und
erhöht die Generation.

Die Infrastruktur-Schnittstelle kann so aussehen:

```python
class WorkerRecovery(Protocol):
    async def replace(self, slot: BrowserSlot) -> WorkerIncarnation: ...
```

`BrowserSlot` ist hier ein Backend-Modell. Seine ID wird nicht an die
Browser-Worker-API übertragen.

Je nach Plattform bedeutet `replace`:

- Kubernetes: Pod ersetzen und Readiness abwarten.
- Container-Service: Task oder Container neu erstellen.
- VM: Instanz über Provider oder Supervisor ersetzen.
- Lokal: Worker-Prozess über einen Supervisor neu starten.

Ein Worker darf sich nur dann selbst beenden, wenn eine Restart-Policy garantiert
vorhanden ist. Andernfalls bleibt der Slot in Quarantäne und löst einen Alarm
aus.

## Backend-Invarianten

Die Zustände können grundsätzlich bestehen bleiben:

```text
LEASED -> RECYCLING -> STOPPED
                 |
                 v
               FAILED -> Retry -> Worker-Ersetzung -> STOPPED
```

Optional kann `QUARANTINED` einen dauerhaft defekten Slot deutlicher von einem
temporären `FAILED` unterscheiden.

Zwingend sind folgende Regeln:

- `RECYCLING`, `FAILED` und `QUARANTINED` sind nicht planbar.
- Die Lease wird erst `RELEASED`, wenn Cleanup oder Worker-Ersetzung bestätigt
  wurde.
- Die Backend-Generation wird erst nach bestätigter physischer Fence erhöht.
- Verspätete Ergebnisse dürfen nur schreiben, wenn Slot, erwartete Generation
  und Recovery-Zustand noch übereinstimmen.
- Die Recovery wird persistent gespeichert und kann nach einem Scheduler-Crash
  von einem neuen Leader fortgesetzt werden.
- Die `slot.id` bleibt ausschließlich in der Control Plane.

## Fehlerbehandlung

| Situation | Worker | Backend-Slot | Reaktion |
| --- | --- | --- | --- |
| Release derselben Generation erneut | laufende Task teilen oder Erfolg wiederholen | unverändert | idempotent |
| Release einer anderen Generation | keine Mutation | unverändert | als veraltet ablehnen |
| Einzelner Cleanup-Fehler | `POISONED` | `FAILED` | Backoff-Retry |
| Cleanup-Timeout | `POISONED` | `FAILED` | Chromium stoppen, Retry zählen |
| Worker nicht erreichbar | unbekannt | `FAILED` | Health prüfen, dann ersetzen |
| Retry-Grenze erreicht | `POISONED` | `QUARANTINED`/`FAILED` | Worker ersetzen |
| Neue Instanz ist ready | `EMPTY` | `STOPPED` | Lease finalisieren, Generation erhöhen |
| Nur Garbage-Löschung schlägt fehl | `EMPTY` | planbar | Garbage-Retry und Disk-Alarm |

## Konkrete Umsetzungsreihenfolge

### Phase 1: Single-Browser-Modell abschließen

- `browser_id` aus `RunningBrowser` entfernen.
- `browser_id` aus Create-, Inspect- und Release-Schemas entfernen.
- Service-Signaturen auf `create(generation)` und `release(generation)`
  reduzieren.
- Die bereits singulären `/browser`-Routen konsequent beibehalten.
- Backend-Provisioner überträgt an den Worker nur die Generation.

### Phase 2: Release deterministisch machen

- Release-Task pro Generation koaleszieren und abschirmen.
- Einzel- und Gesamttimeouts einführen.
- unabhängige Cleanups parallel versuchen und alle Ergebnisse sammeln.
- Chromium-Stop immer ausführen.
- Handles erst nach erfolgreichem Cleanup entfernen.
- Postconditions prüfen und Create nur bei Erfolg entsperren.

### Phase 3: Langsame Dateilöschung entkoppeln

- generation-spezifischen Runtime-Workspace verwenden.
- alten Workspace atomar isolieren.
- Garbage-Verzeichnisse im Hintergrund mit Retry löschen.

### Phase 4: Harte Recovery anbinden

- Backoff, Jitter, Maximalversuche und maximales Recovery-Alter persistieren.
- `instance_id` im Health-Endpunkt bereitstellen.
- `WorkerRecovery` für die verwendete Plattform implementieren.
- Worker nach der Retry-Grenze ersetzen und neue Readiness bestätigen.

## Minimale Validierung

Im aktuellen Projektstadium genügen gezielte Smoke-Tests:

1. Worker-Requests und Worker-Zustand enthalten keine Browser-ID.
2. Die singulären `/browser`-Routen funktionieren.
3. Ein Generation-Mismatch verändert die laufende Runtime nicht.
4. Zwei Release-Aufrufe derselben Generation teilen eine Operation.
5. Caller-Cancellation beendet die interne Release-Task nicht.
6. Ein hängender Cleanup endet durch Timeout; Chromium-Stop wird trotzdem
   versucht.
7. Ein fehlgeschlagenes `close` behält den Handle für den Retry.
8. Nur ein vollständig erfolgreicher Release entsperrt `create`.
9. Nach der Retry-Grenze wird genau eine Worker-Ersetzung gestartet.
10. Nur eine neue und bereite `instance_id` macht den Backend-Slot wieder
    planbar.

## Entscheidung

Der Worker wird konsequent als singuläre Browser-Ressource modelliert. Er kennt
keine `browser_id`; die `slot.id` bleibt ausschließlich im Backend. Die
aktuellen `/browser`-Routen drücken dieses Modell bereits aus.

Die Generation schützt vor verspäteten Control-Plane-Befehlen. Release-Schritte
werden begrenzt, idempotent und retry-sicher ausgeführt. Ein unsauberer Worker
bleibt gesperrt. Kann er sich innerhalb einer festen Grenze nicht bereinigen,
wird die gesamte Worker-Instanz ersetzt. Dadurch bleibt die Session-Isolation
korrekt, ohne dass ein defekter Cloud-Slot dauerhaft im Release-Zustand hängt.
