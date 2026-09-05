from pyrpckit.schema import render_json_schema, render_openrpc

from backend.browser_tunnel.presentation.rpc import BROWSER_PROTOCOL


def browser_json_schema() -> dict:
    return render_json_schema(
        BROWSER_PROTOCOL,
        title="BrowserTunnel JSON-RPC Protocol",
        schema_id="/api/v1/browser/schema.json",
    )


def browser_openrpc_schema() -> dict:
    return render_openrpc(
        BROWSER_PROTOCOL,
        title="BrowserTunnel",
        servers=({"name": "browser-tunnel", "url": "/api/v1/browser/ws"},),
    )
