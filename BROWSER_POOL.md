# Browser Pool: Worker Discovery hinter ein Interface

Status: Schritte 1 und 2 aus §7 sind umgesetzt, 3 und 4 offen.
Ausgangspunkt: `backend/src/backend/features/browsers/infrastructure/settings.py`

## 1. Was heute passiert

```python
class BrowserPoolSettings(BaseSettings):
    browser_worker_1_url: str = "http://127.0.0.1:8011"
    browser_worker_2_url: str = "http://127.0.0.1:8012"

    def slots(self) -> tuple[BrowserSlot, BrowserSlot]: ...
```

Die Klasse macht drei Dinge gleichzeitig, die nichts miteinander zu tun haben:

1. **Konfiguration lesen** (env -> URL),
2. **Membership festlegen** (es gibt genau zwei Worker),
3. **Identität vergeben** (die hartkodierten UUIDs `...0001` / `...0002`).

Punkt 3 ist der eigentlich interessante. Die Slot-Id ist heute eine Konstante im
Code, und der Rest des Systems verlässt sich darauf: `BrowserService.start()`
macht ein Upsert auf denselben Ids, `SqlSessionRequestRepository.reconcile()`
schreibt sie erneut, Leases referenzieren sie. Genau diese Stabilität ist der
Grund, warum ein Backend-Neustart den Pool nicht zerstört — und genau sie fällt
weg, sobald Worker dynamisch dazukommen.

Weitere Symptome derselben Wurzel:

- `slots() -> tuple[BrowserSlot, BrowserSlot]` friert die Kardinalität im
  **Typ** ein. Ein dritter Worker ist ein Typfehler, kein Konfigwechsel.
- `BrowserPoolSettings` ist Infrastruktur der `browsers`-Feature, wird aber quer
  von `session_requests` importiert — im `Dispatcher.__init__` und in
  `SqlSessionRequestRepository.reconcile(settings)`. Ein anderes Feature hängt
  also nicht an einem Port, sondern an einer konkreten Settings-Klasse eines
  fremden Features.
- Discovery ist synchron und total: es gibt keinen Weg auszudrücken, dass ein
  Worker *verschwunden* ist, nur dass er in der Liste steht oder nicht.

Nicht schlimm bei zwei Workern. Aber die Kopplung sitzt an genau den Stellen, an
denen später die Data-Plane-Fähigkeiten hin sollen.

## 2. Zielbild in einem Satz

Der Pool besteht aus einer **beobachteten Menge von Workern**, die eine
austauschbare Quelle liefert, und die Persistenzschicht *gleicht ab* statt neu
zu schreiben. Das ist die klassische Trennung „Discovery liefert Ist,
Reconciler zieht Soll nach" — dieselbe Form wie Kubernetes-Endpoints oder ein
Consul-Watch, nur eine Nummer kleiner.

## 3. Der Vorschlag: `BrowserWorkerDirectory`

Ein einziger neuer Port in `features/browsers/application/ports.py`, bewusst
minimal, aber mit den Feldern, an denen die späteren Strategien andocken.

```python
# domain/models.py

@dataclass(frozen=True, slots=True)
class BrowserWorker:
    """One worker as the directory currently observes it."""

    id: UUID                      # stabil über Neustarts, siehe §4
    url: str
    capacity: int = 1
    labels: Mapping[str, str] = field(default_factory=dict)

    def slots(self) -> tuple[BrowserSlot, ...]: ...
```

```python
# application/ports.py

class BrowserWorkerDirectory(ABC):
    """Woher der Pool erfährt, welche Worker es gibt."""

    @abstractmethod
    async def snapshot(self) -> Sequence[BrowserWorker]:
        """Die aktuell bekannten Worker. Vollständig, nicht inkrementell."""
```

Das ist alles, was heute gebraucht wird. `StaticBrowserWorkerDirectory` liest
die URLs aus den Settings und ist zunächst die einzige Implementierung.
`BrowserWorkerProvisioner` bekommt das Directory statt der Settings injiziert,
`provision()` wird zu `directory.snapshot()`.

### Warum `snapshot()` und nicht `list()` / `slots()`

Der Name sagt, dass das Ergebnis ein **Zeitpunkt** ist und nicht die Wahrheit.
Wer `slots()` liest, denkt „das ist die Konfiguration". Wer `snapshot()` liest,
denkt „das kann beim nächsten Aufruf anders sein" — und genau dieses Denken
brauchen wir an den Aufrufstellen, *bevor* die erste dynamische Quelle kommt.

### Was bewusst *nicht* im Interface steht

- **Kein `watch()` / `AsyncIterator`.** Push-Discovery ist die Erweiterung,
  nicht die Basis. Sie kommt als optionale zweite Methode oder als eigener Port
  dazu, wenn die erste Quelle sie anbietet. Bis dahin ist Polling über
  `snapshot()` korrekt und trivial.
- **Kein `register()` / `deregister()`.** Solange Worker nicht selbst beim
  Backend anklopfen, wäre das erfundene API-Fläche. Self-Registration hat eine
  eigene Auth-Story und wird dann ein eigener Port.
- **Kein Health / Heartbeat.** Erreichbarkeit gehört zum Provisioner bzw. zum
  Zustandsautomaten (`BrowserState.FAILED`), nicht zur Mitgliedschaft. Ein
  Worker, der gerade nicht antwortet, ist trotzdem Teil des Pools.
- **Keine Auswahl-/Placement-Logik.** Das Directory sagt, *was es gibt*, nicht
  *was genommen wird*. Auswahl bleibt im Repository (`find_available` /
  `claim`), siehe §6.

## 4. Der harte Teil: Identität

Sobald die Worker-Liste nicht mehr im Code steht, muss die Id von *irgendwo*
kommen und über Neustarts stabil bleiben. Drei Optionen:

| Ansatz | Bewertung |
|---|---|
| UUID pro Boot neu generieren | Fällt aus. Leases und die `browsers`-Tabelle brechen bei jedem Neustart. |
| Id aus der DB, URL als natürlicher Schlüssel | Funktioniert, macht das Directory aber DB-abhängig — die Quelle müsste schreiben. |
| **Deterministisch aus der Worker-Identität ableiten** | `uuid5(NAMESPACE, identity)`. Keine Koordination, kein State, überall stabil. |

Empfehlung: **UUIDv5**. Die `identity` ist das, was die jeweilige Quelle als
dauerhaft garantieren kann — bei der statischen Quelle die konfigurierte URL,
bei Kubernetes der Pod-Name eines StatefulSets, bei einem Cloud-Provider die
Instance-Id. Das Directory ist damit die einzige Stelle, die weiß, was einen
Worker ausmacht, und die hartkodierten `...0001`/`...0002` verschwinden.

Eine Konsequenz, die man bewusst akzeptieren muss: Ändert sich die URL eines
statisch konfigurierten Workers, ist es aus Sicht des Pools ein *anderer*
Worker. Bei zwei lokalen Ports ist das harmlos, und bei allem Dynamischen ist
es ohnehin richtig — dort ist die Identity dann nicht mehr die URL.

## 5. Reconcile statt Upsert

Heute schreiben `BrowserService.start()` und
`SqlSessionRequestRepository.reconcile()` die konfigurierten Slots per
`on_conflict_do_nothing` in die Tabelle. Der Fall „Zeile existiert, Worker ist
aber nicht mehr in der Liste" kommt schlicht nicht vor, weil die Liste konstant
ist.

Mit dynamischer Discovery braucht es drei Fälle:

- **Neu** (im Snapshot, nicht in der DB) -> Zeile anlegen, `STOPPED`.
- **Bekannt** (in beidem) -> URL nachziehen, aber nur wenn `STOPPED`. Genau das
  macht der Code heute schon, mit dem richtigen Kommentar dazu („Never redirect
  a running lease to a different worker").
- **Verschwunden** (in der DB, nicht im Snapshot) -> **nicht löschen**. Der
  Zustand dafür fehlt aktuell; `BrowserState` braucht einen Wert wie `DRAINING`
  oder `ORPHANED`: nicht mehr vergebbar (`is_available` -> `False`), eine
  laufende Lease läuft aber zu Ende, und erst danach fällt die Zeile weg.
  Löschen wäre falsch, solange eine Lease darauf zeigt.

Das ist der eigentliche Gewinn: Die Reconcile-Schleife wird *einmal* richtig
geschrieben und ist danach für jede Quelle korrekt.

Nebenbei sollte `reconcile` dabei vom `session_requests`-Repository in die
`browsers`-Feature wandern. Dass ein fremdes Repository die Browser-Tabelle
seedet, ist die zweite Ausprägung derselben Kopplung wie in §1.

## 6. Capabilities — was danach möglich wird

`labels` auf `BrowserWorker` ist der Platzhalter, an dem die
Data-Plane-Fähigkeiten andocken, ohne dass das Interface sich nochmal ändert.
Realistische Kandidaten:

- **Placement nach Anforderung.** Ein Session-Request bringt Constraints mit
  (Region, Browser-Version, Proxy-Exit, GPU). `claim()` filtert dann nicht nur
  auf `state`, sondern auf ein Constraint-Matching. Dafür müssen die Labels in
  der `browsers`-Tabelle mitgeschrieben werden — sonst müsste die Auswahl den
  Snapshot in Python joinen, und das macht den
  `FOR UPDATE SKIP LOCKED`-Mechanismus in `claim()` kaputt.
  **Labels gehören persistiert.**
- **Mehr als ein Browser pro Worker.** `capacity` trägt das schon: `slots()`
  gibt *n* Slots zurück, deren Ids aus `uuid5(worker_id, index)` fallen. Es
  fehlt nur eine Quelle, die etwas anderes als 1 meldet.
- **Skalierung.** Ein `ScalingBrowserWorkerDirectory` fordert auf Basis der
  Queue-Länge Worker an. Das ist eine *Implementierung* des Ports plus ein
  zweiter Port zum Anfordern — das Interface aus §3 ändert sich nicht.
- **Kosten-/Zonen-Awareness.** Labels plus eine Sortierregel in `claim()`.

## 7. Vorgeschlagene Reihenfolge

1. ~~`BrowserWorker` + `BrowserWorkerDirectory` einführen,
   `StaticBrowserWorkerDirectory` aus den Settings, Ids via UUIDv5. Settings
   werden zu einer Liste, `tuple[BrowserSlot, BrowserSlot]` wird
   `Sequence[BrowserWorker]`.~~ **erledigt**
2. ~~`BrowserPoolSettings` aus `session_requests` entfernen — Dispatcher und
   Repository bekommen den Port bzw. den fertigen Snapshot.~~ **erledigt**
3. `reconcile` in die `browsers`-Feature ziehen und um den
   „verschwunden"-Fall + `DRAINING` erweitern.
4. Erst danach, und nur bei echtem Bedarf: zweite Directory-Implementierung,
   `watch()`, Labels in der Tabelle, Capacity > 1.

Schritt 1 und 2 sind reines Refactoring ohne Verhaltensänderung und lohnen sich
schon bei zwei Workern, weil sie die Import-Kopplung auflösen. Schritt 3 ändert
Verhalten und braucht eine Migration (neuer Enum-Wert).

## 8. Kleinere Anmerkungen zum jetzigen Code

- `BrowserWorkerProvisioner._provisioned` / `_generations` halten Zustand im
  Prozess, der auch in der DB steht (`Browser.generation`). Bei mehreren
  Backend-Instanzen ist der Prozess-Cache falsch. Einziger Nutzer ist
  `deprovision()` — das könnte genauso gut über das Repository gehen.
- `BrowserWorkerRoutes` baut URLs per String-Manipulation aus
  `slot.browser_worker_url`. Sauber, aber konzeptionell gehört das zum Worker,
  nicht zum Slot — nach dem Refactoring wäre `BrowserWorker` der richtige
  Parameter.
- `Browser.is_available` prüft auf das Tupel `(READY, STOPPED)`. Mit einem
  `DRAINING`-Zustand wird daraus besser eine explizite Negativliste oder ein
  Feld am Enum, damit ein neuer Zustand nicht versehentlich als „vergebbar"
  durchrutscht.

## 9. Nachtrag zur Umsetzung von Schritt 1 und 2

- Env-Variable ist `BACKEND_BROWSER_POOL_WORKER_URLS` (comma-separated). Der
  Prefix musste `BACKEND_BROWSER_POOL_` werden, weil `BACKEND_BROWSER_WORKER_`
  bereits von `BrowserWorkerSettings` belegt ist. `worker_urls` trägt ein
  `NoDecode` plus zwei Validatoren: einen zum Splitten (sonst erwartet
  pydantic-settings JSON) und einen, der doppelte URLs ablehnt — die URL ist
  hier die Identität, ein Duplikat würde zwei Slots zu einem verschmelzen.
- `BrowserSlot` bleibt bestehen und ist weiterhin das, womit Provisioner,
  Routes und Repository arbeiten. `BrowserWorker` sitzt eine Ebene darüber:
  Discovery liefert Worker, `slots_of()` macht daraus die Slots. Damit ist die
  Änderung auf die Pool-Ränder begrenzt.
- **Die Slot-Ids ändern sich.** Aus `...0001`/`...0002` werden abgeleitete
  UUIDv5-Werte. Bestehende `browsers`-Zeilen werden dadurch nicht migriert,
  sondern beim nächsten Reconcile durch neue ergänzt; die alten bleiben als
  Karteileichen stehen. Für eine Umgebung mit echten Daten braucht es entweder
  eine Migration, die die beiden bekannten Ids umschreibt, oder ein einmaliges
  Leeren der Tabelle. Das ist genau der Fall, den Schritt 3 sauber löst.
