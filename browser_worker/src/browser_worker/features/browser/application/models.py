from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserEndpoint:
    public_base_url: str
