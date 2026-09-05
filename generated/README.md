# Generated internal HTTP clients

Typed async clients for the internal APIs, rendered from the FastAPI OpenAPI
documents by [httpxgen](https://github.com/mathisarends/httpxgen). Import them
from the infrastructure layer:

```python
import httpx

from generated.browser_worker import CreateBrowserRequest, GeneratedBrowserWorkerClient

async with httpx.AsyncClient() as http:
    client = GeneratedBrowserWorkerClient(http, base_url)
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
./scripts/generate_http_clients.sh          # rewrite the clients
./scripts/generate_http_clients.sh --check  # fail if out of date
```

The script exports each FastAPI app's OpenAPI document to `schemas/*.json`
(`scripts/export_openapi_schemas.py` — httpxgen has no notion of a FastAPI
app, so this part stays Python) and then runs the `httpxgen` CLI directly
against those files.

Never edit the files under `src/generated/<api>/` by hand — change the FastAPI
routers or schemas and regenerate. Failed requests raise `generated.<api>.ApiError`.
