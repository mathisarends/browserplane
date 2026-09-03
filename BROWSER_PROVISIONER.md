# Browser Provisioner: minimaler Zwei-Browser-MVP

## Zielbild

Die V1 trennt drei Verantwortlichkeiten in eigene Python-Packages:

```text
Frontend ──HTTP──▶ control-plane
    │                  │ Browser-Lifecycle
    │ JSON-RPC/WS      ▼
    ├────────────▶ browsertunnel ──rohes CDP──▶ data-plane worker ──▶ Chromium
    └──────────── binärer Screencast-WS ──────▶       │
```

Die Control Plane kennt Browser-IDs, Worker und öffentliche Tunnel-Adressen. Ein
Data-Plane-Worker besitzt genau einen Browserprozess und stellt create,
inspect, destroy, CDP, Screencast sowie health bereit. BrowserTunnel ist ein
Consumer dieser Data Plane und übersetzt CDP in das JSON-RPC-, Input- und
Status-Protokoll des Frontends.

Dieses Session-Modell entspricht dem grundlegenden Muster von Browserbase
(`id`, Status und geheime `connectUrl`) und Browser Use Cloud (eine
Browser-Session ist über CDP steuerbar):

- [Browserbase: Using a browser session](https://docs.browserbase.com/platform/browser/getting-started/using-browser-session)
- [Browserbase: Session resource](https://docs.browserbase.com/reference/api/get-a-session)
- [Browser Use: Cloud browser and CDP model](https://github.com/browser-use/browser-use/blob/main/CLOUD.md)

## Aktueller V1-Schnitt

```text
control-plane/
  src/control_plane/
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

browsertunnel/
  src/browsertunnel/  # CDP-Consumer und Frontend-Protokoll

data-plane/
  src/data_plane/     # Chromium-Lifecycle, Registry, CDP-Proxy, Kapazität
```

`DataPlaneBrowserProvisioner` erzeugt beim Start über die interne Worker-API
zwei feste Browser-Ressourcen. Erst danach starten die BrowserTunnel-Container
und verbinden sich mit deren CDP-Endpunkten. Die Control Plane liefert dem
Frontend den öffentlichen WebSocket-Endpunkt des ausgewählten BrowserTunnel
und den separaten Screencast-Endpunkt der Data Plane. Beide WebSocket-Ströme
umgehen die Control Plane; rohe CDP-Adressen bleiben intern.

Die minimale Provisioner-Schnittstelle lautet:

```python
class BrowserProvisioner(Protocol):
    async def provision(self) -> Sequence[BrowserSlot]: ...
    async def deprovision(self) -> None: ...
```

Für Browserbase oder Browser Use wird später die Worker- beziehungsweise
Provisioner-Implementierung ersetzt. `browsertunnel` benötigt weiterhin nur
einen CDP-Endpunkt und muss den Browser-Provider nicht kennen.

## Öffentliche Schnittstellen

Browser auflisten:

```http
GET /api/v1/browsers
```

```json
[
  {
    "id": "browser-1",
    "status": "ready",
    "websocket_url": "ws://localhost:8021/api/v1/browser/ws",
    "screencast_url": "ws://localhost:8011/api/v1/browser/browser-1/screencast"
  },
  {
    "id": "browser-2",
    "status": "ready",
    "websocket_url": "ws://localhost:8022/api/v1/browser/ws",
    "screencast_url": "ws://localhost:8012/api/v1/browser/browser-2/screencast"
  }
]
```

Mit einem Browser verbinden: Das Frontend verwendet `websocket_url` für die
Steuerung über BrowserTunnel und `screencast_url` für binäre JPEG-Frames von
der Data Plane.

```text
WS ws://localhost:8021/api/v1/browser/ws
WS ws://localhost:8011/api/v1/browser/browser-1/screencast
```

Die Browser-Verbindung erfolgt über den browser-spezifischen Endpunkt. Die
JSON-RPC-Nachrichten selbst ändern sich nicht.

## Lokal starten

```bash
docker compose up --build
```

Danach ist die Control Plane unter `http://localhost:8000` erreichbar. Die
beiden Data Planes sind auf 8011 und 8012 und die BrowserTunnel auf 8021 und
8022 für direkte Client-Verbindungen erreichbar.

## Bewusste Grenzen

- Genau zwei eager gestartete Browser, keine dynamische Skalierung.
- Registry nur im Speicher, keine Datenbank oder Queue.
- Compose besitzt den Worker- und Tunnel-Container-Lifecycle; die Control Plane
  besitzt den Browser-Lifecycle auf den Workern.
- Worker-Health und Kapazität sind vorhanden, werden aber noch nicht für
  dynamisches Scheduling verwendet.
- Noch keine exklusive Viewer-Sperre, Authentifizierung oder Wiederherstellung.
- Cloud-CDP-URLs dürfen später niemals in Logs oder API-Antworten erscheinen.

Der nächste Schritt wäre eine echte Session-API, die Worker nach Kapazität
auswählt und BrowserTunnel-Workloads dynamisch zuordnet. Der aktuelle Schnitt
zeigt dafür bereits die getrennten Lifecycles.
