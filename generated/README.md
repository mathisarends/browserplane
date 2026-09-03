# Generated internal HTTP clients

Typed async clients for the internal APIs, rendered from the FastAPI OpenAPI
documents. Import them from the infrastructure layer:

```python
from generated.data_plane import CreateBrowserRequest, DataPlaneClient

async with DataPlaneClient(base_url) as client:
    browser = await client.create_browser(CreateBrowserRequest(id=browser_id))
```

## Layout

- `src/generated/transport.py` — hand-written HTTP transport shared by the clients.
- `src/generated/<api>/` — generated `models.py`, `client.py` and `__init__.py`.

## Regenerating

```bash
uv run python scripts/generate_http_clients.py          # rewrite the clients
uv run python scripts/generate_http_clients.py --check  # fail if out of date
```

Never edit the files under `src/generated/<api>/` by hand — change the FastAPI
routers or schemas and regenerate. Failed requests raise `httpx2.HTTPStatusError`.
