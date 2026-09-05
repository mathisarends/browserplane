"""Typed HTTP clients rendered from the internal OpenAPI documents by httpxgen."""

from httpx2 import alias_httpx

# The generated clients import plain `httpx`; alias it to httpx2 before any of
# them do so, since only httpx2 is installed in this workspace.
alias_httpx()

__all__: list[str] = []
