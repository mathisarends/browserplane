# Browser Provisioner: minimaler Zwei-Browser-MVP

## Zielbild

Die V1 trennt die Verantwortlichkeiten in Backend und Data Plane:

```text
Frontend ── HTTP/JSON-RPC/WS ──▶ Backend ── internes CDP/HTTP/WS ──▶ Data Plane ──▶ Chromium
```

Das Backend kennt Browser-IDs und Worker, veröffentlicht aber keine internen
Worker- oder CDP-Adressen. Ein
Data-Plane-Worker besitzt genau einen Browserprozess und stellt create,
inspect, destroy, CDP, Screencast, Video-Recordings sowie health bereit. Das
Backend übersetzt CDP direkt in das JSON-RPC-, Input- und Status-Protokoll des
Frontends.

Dieses Session-Modell entspricht dem grundlegenden Muster von Browserbase
(`id`, Status und geheime `connectUrl`) und Browser Use Cloud (eine
Browser-Session ist über CDP steuerbar):

- [Browserbase: Using a browser session](https://docs.browserbase.com/platform/browser/getting-started/using-browser-session)
- [Browserbase: Session resource](https://docs.browserbase.com/reference/api/get-a-session)
- [Browser Use: Cloud browser and CDP model](https://github.com/browser-use/browser-use/blob/main/CLOUD.md)

## Aktueller V1-Schnitt

```text
backend/
  src/backend/
    app.py                     # Router-Komposition und Fehler-Handler
    settings.py                # Konfiguration der Browser-Slots
    exceptions.py              # ControlPlaneException als Basis
    presentation/              # API-Fehlerkontrakt
      api_errors.py            # ApiErrorSpec, Responses, Exception-Handler
      errors.py                # ApiErrorCode, ApiErrorResponse
    features/
      browsers/
        application/           # Modelle, Ports, BrowserService, Exceptions
        infrastructure/        # Data-Plane-Provisioner und Registry
        presentation/          # Router, Schemas, Mapper, Fehler-Specs
      leases/
        application/           # Lease-Modell, LeaseStore/BrowserAllocator, Service
        infrastructure/        # In-Memory-Store, Allocator-Adapter
        presentation/          # Router, Schemas, Mapper, Fehler-Specs
      health/presentation/     # health und readiness

    browser_tunnel/             # CDP-Consumer und Frontend-Protokoll

data-plane/
  src/data_plane/     # Chromium-Lifecycle, Registry, CDP-Proxy, Kapazität
```

`DataPlaneBrowserProvisioner` erzeugt beim Start über die interne Worker-API
zwei feste Browser-Ressourcen. Das Backend verbindet seinen sessiongebundenen
JSON-RPC-Endpunkt direkt mit dem jeweiligen internen CDP-Endpunkt und proxyt
auch den Screencast. Der Client spricht ausschließlich mit dem Backend.

Die minimale Provisioner-Schnittstelle lautet:

```python
class BrowserProvisioner(Protocol):
    async def provision(self) -> Sequence[BrowserSlot]: ...
    async def deprovision(self) -> None: ...
```

Für Browserbase oder Browser Use wird später die Worker- beziehungsweise
Provisioner-Implementierung ersetzt. Der integrierte Browser-Tunnel benötigt
weiterhin nur einen CDP-Endpunkt und muss den Browser-Provider nicht kennen.

## Öffentliche Schnittstellen

Eine Session öffnen:

```http
POST /api/v1/sessions
```

```json
{
  "owner_id": "00000000-0000-0000-0000-000000000007",
  "ttl_seconds": 600
}
```

Die Antwort enthält ausschließlich backend-relative Pfade für JSON-RPC und
binäre JPEG-Frames. Worker-Adressen sind nicht Teil des Client-Vertrags.

```text
WS ws://localhost:8000/api/v1/sessions/{session_id}/tunnel
WS ws://localhost:8000/api/v1/sessions/{session_id}/screencast
```

Die Browser-Verbindung erfolgt über den browser-spezifischen Endpunkt. Die
JSON-RPC-Nachrichten selbst ändern sich nicht.

## Video-Recording

Die Data Plane nimmt über `Page.startScreenRecording` auf und folgt dabei dem
aktiven Tab. Welcher Tab aktiv ist, weiß der `ActiveTabStream`: Er hält pro
Browser genau eine CDP-Verbindung, screencastet jedes Page-Target — nur während
eines Screencasts meldet CDP Sichtbarkeit — und verteilt die Updates an alle
Konsumenten. Live-Viewer lesen daraus die Frames, der Recorder die
Tab-Wechsel; die Verbindung besteht, solange mindestens ein Konsument
subscribed ist. Wer später dazukommt, bekommt den aktuellen aktiven Tab
nachgereicht, weil das Zustand ist und kein Event.

`Page.startScreenRecording` hängt an genau einem Target und folgt einem
Tab-Wechsel nicht. Eine Aufnahme besteht deshalb aus einem Segment pro Tab: Bei
jedem Wechsel wird die laufende Aufnahme gestoppt, der IO-Stream in eine Datei
gedrained und auf dem neuen Tab neu gestartet. Chromium liefert derzeit MP4;
der Container wird aus dem Datei-Header erkannt. Die Dateien liegen bis zum
Shutdown des Workers in einem temporären Verzeichnis.

```text
POST /api/v1/browser/{browser_id}/recordings                     # startet
POST /api/v1/browser/{browser_id}/recordings/{recording_id}/stop # beendet
GET  /api/v1/browser/{browser_id}/recordings/{recording_id}      # Status + Segmente
GET  /api/v1/browser/{browser_id}/recordings/{recording_id}/file # Video, einsegmentig
GET  .../recordings/{recording_id}/segments/{index}/file         # Video eines Tabs
```

Der `file`-Endpunkt liefert das Video, solange die Aufnahme auf einem Tab
geblieben ist, und antwortet sonst mit `recording_has_segments`; die Segmente
stehen mit Index, Target und Zeitraum im Status und einzeln unter
`segments/{index}/file`.

## Lokal starten

```bash
docker compose up --build
```

Danach ist das Backend unter `http://localhost:8000` erreichbar. Die beiden
Data Planes sind lokal auf 8011 und 8012 erreichbar; der Client verwendet sie
nicht direkt.

## Bewusste Grenzen

- Genau zwei eager gestartete Browser, keine dynamische Skalierung.
- Registry nur im Speicher, keine Datenbank oder Queue.
- Compose besitzt den Worker-Container-Lifecycle; das Backend besitzt den
  Browser- und Session-Lifecycle auf den Workern.
- Worker-Health und Kapazität sind vorhanden, werden aber noch nicht für
  dynamisches Scheduling verwendet.
- Noch keine exklusive Viewer-Sperre, Authentifizierung oder Wiederherstellung.
- Cloud-CDP-URLs dürfen später niemals in Logs oder API-Antworten erscheinen.

Die Session-API wählt einen freien Browser aus dem Pool und hält alle internen
Verbindungsdaten vom Client fern.
