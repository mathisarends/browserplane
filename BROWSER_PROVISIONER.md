# Browser Provisioner: minimaler Zwei-Browser-MVP

## Zielbild

Die V1 trennt drei Verantwortlichkeiten in eigene Python-Packages:

```text
Frontend ──HTTP/WS──▶ control-plane ──WS-Routing──▶ browsertunnel
                           │                            │
                           │ Browser-Lifecycle          │ rohes CDP
                           ▼                            ▼
                    data-plane worker ─────────────▶ Chromium
```

Die Control Plane kennt Browser-IDs, Worker und interne Tunnel-Adressen. Ein
Data-Plane-Worker besitzt Browserprozesse und stellt create, inspect, destroy,
CDP sowie health/capacity bereit. BrowserTunnel ist ein Consumer dieser Data
Plane und übersetzt CDP in das konkrete JSON-RPC-, Input- und
Screencast-Protokoll des Frontends.

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
    app.py            # FastAPI-Aufbau
    router.py         # öffentliche HTTP-/WebSocket-Routen
    provider.py       # Dishka-Verdrahtung
    provisioning.py  # austauschbarer Provisioner-Port
    registry.py       # zwei Browser-Slots
    proxy.py          # bidirektionaler WebSocket-Proxy

browsertunnel/
  src/browsertunnel/  # CDP-Consumer und Frontend-Protokoll

data-plane/
  src/data_plane/     # Chromium-Lifecycle, Registry, CDP-Proxy, Kapazität
```

`DataPlaneBrowserProvisioner` erzeugt beim Start über die interne Worker-API
zwei feste Browser-Ressourcen. Erst danach starten die BrowserTunnel-Container
und verbinden sich mit deren CDP-Endpunkten. Die Control Plane leitet den
Client-WebSocket an den ausgewählten BrowserTunnel weiter. Worker-, CDP- und
interne Tunnel-Adressen werden nicht an das Frontend gegeben.

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
    "websocket_url": "/api/v1/browsers/browser-1/ws"
  },
  {
    "id": "browser-2",
    "status": "ready",
    "websocket_url": "/api/v1/browsers/browser-2/ws"
  }
]
```

Mit einem Browser verbinden:

```text
WS /api/v1/browsers/{browser_id}/ws
```

Die Browser-Verbindung erfolgt über den browser-spezifischen Endpunkt. Die
JSON-RPC-Nachrichten selbst ändern sich nicht.

## Lokal starten

```bash
docker compose up --build
```

Danach ist die Control Plane unter `http://localhost:8000` erreichbar. Die
beiden BrowserTunnel-Container sind nur im internen Compose-Netz sichtbar.

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
