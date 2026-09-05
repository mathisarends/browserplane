# Generated internal HTTP clients

Typed async clients for the internal APIs, rendered from the FastAPI OpenAPI
documents by [httpxgen](https://github.com/mathisarends/httpxgen). Import them
from the infrastructure layer:

```python
import httpx

from generated.data_plane import CreateBrowserRequest, GeneratedDataPlaneClient

async with httpx.AsyncClient() as http:
    client = GeneratedDataPlaneClient(http, base_url)
    browser = await client.create_browser(CreateBrowserRequest(id=browser_id))
```

The generated code imports plain `httpx`, which is a declared dependency here
so the import resolves for type checkers and IDEs. At runtime,
`generated/__init__.py` redirects it to `httpx2` — the HTTP client actually
used across this workspace — via `alias_httpx()`, before any client module is
imported.

## Layout

- `src/generated/__init__.py` — registers the `httpx` → `httpx2` alias.
- `src/generated/<api>/` — rendered by httpxgen: `client.py`, `models.py`,
  `exceptions.py`, `http_methods.py`, `serialization.py`.

## Regenerating

```bash
uv run python scripts/generate_http_clients.py          # rewrite the clients
uv run python scripts/generate_http_clients.py --check  # fail if out of date
```

Never edit the files under `src/generated/<api>/` by hand — change the FastAPI
routers or schemas and regenerate. Failed requests raise `generated.<api>.ApiError`.
