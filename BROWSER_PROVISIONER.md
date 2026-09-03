# Browser Provisioner: minimaler Zwei-Browser-MVP

## Zielbild

Die V1 besteht aus zwei getrennten Python-Services und UV-Workspace-Membern:

```text
                         control-plane
                    Registry + WebSocket-Proxy
                       /               \
              browser-1                 browser-2
                  |                         |
          browsertunnel-1           browsertunnel-2
          (eine Data Plane)          (eine Data Plane)
                  |                         |
             Chromium 1                Chromium 2
```

Die Control Plane kennt Browser-IDs, Kapazität und die internen Tunnel-Adressen.
BrowserTunnel bleibt eine Single-Browser-Data-Plane für Navigation, Input,
Tabs, Clipboard und Screencast. Der Browser selbst ist eine provisionierte
Ressource und kein weiterer UV-Member.

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
  src/browsertunnel/  # bestehende Data Plane, weiterhin ein Browser
```

`ComposeBrowserProvisioner` liefert beim Start zwei feste Slots. Compose hält
dazu zwei getrennte BrowserTunnel-Container; jeder startet momentan seinen
eigenen lokalen Chromium. Die Control Plane leitet den Client-WebSocket an den
ausgewählten Container weiter. Interne Tunnel-Adressen werden nicht an das
Frontend gegeben.

Die minimale Provisioner-Schnittstelle lautet:

```python
class BrowserProvisioner(Protocol):
    async def provision(self) -> Sequence[BrowserSlot]: ...
    async def deprovision(self) -> None: ...
```

Für Browserbase oder Browser Use wird später nur diese Implementierung ersetzt:
Cloud-Browser erzeugen, eine BrowserTunnel-Data-Plane mit dessen geheimer
CDP-URL starten und beim Freigeben beides wieder beenden. `browsertunnel` muss
dazu nicht wissen, welcher Cloud-Provider verwendet wird.

## Öffentliche Schnittstellen

Browser auflisten:

```http
GET /api/browsers
```

```json
[
  {
    "id": "browser-1",
    "status": "ready",
    "websocket_url": "/api/browsers/browser-1/ws"
  },
  {
    "id": "browser-2",
    "status": "ready",
    "websocket_url": "/api/browsers/browser-2/ws"
  }
]
```

Mit einem Browser verbinden:

```text
WS /api/browsers/{browser_id}/ws
```

Der bestehende Frontend-Endpunkt `WS /api/browser/ws` bleibt vorerst als Alias
auf `browser-1` erhalten. Die JSON-RPC-Nachrichten selbst ändern sich nicht.

## Lokal starten

```bash
docker compose up --build
```

Danach ist die Control Plane unter `http://localhost:8000` erreichbar. Die
beiden BrowserTunnel-Container sind nur im internen Compose-Netz sichtbar.

## Bewusste Grenzen

- Genau zwei eager gestartete Browser, keine dynamische Skalierung.
- Registry nur im Speicher, keine Datenbank oder Queue.
- Compose besitzt den Container-Lifecycle; die Control Plane bildet ihn ab.
- Noch kein Health-Check der einzelnen Data Planes.
- Noch keine exklusive Viewer-Sperre, Authentifizierung oder Wiederherstellung.
- Cloud-CDP-URLs dürfen später niemals in Logs oder API-Antworten erscheinen.

Der nächste Schritt wäre ein echter Cloud-Provisioner, der Browser-Session und
BrowserTunnel-Workload gemeinsam erzeugt und zerstört. Die öffentliche API und
die Data Plane können dabei unverändert bleiben.
