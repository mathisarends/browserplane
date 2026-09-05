from dataclasses import dataclass

from backend.features.browsers.application.models import Browser
from backend.features.leases.application.models import Lease


@dataclass(frozen=True, slots=True)
class PooledBrowser:
    """One browser slot together with the lease currently holding it, if any.

    The pool and the leases are separate stores on purpose; an operator has to
    see them as one row to tell "free" apart from "leased by whom".
    """

    browser: Browser
    lease: Lease | None = None
