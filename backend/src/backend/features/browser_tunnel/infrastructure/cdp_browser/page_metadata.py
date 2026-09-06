from cdpify import CDPSession
from cdpify.exceptions import CDPCommandException

from backend.features.browser_tunnel.application import BrowserPageMetadata


class CdpPageMetadata(BrowserPageMetadata):
    """Read page metadata through this page's fixed CDP session."""

    def __init__(self, session: CDPSession) -> None:
        self._session = session

    async def favicon_url(self) -> str | None:
        try:
            result = await self._session.runtime.evaluate(
                expression="""
(() => {
  const links = Array.from(document.querySelectorAll('link[rel~="icon"][href]'));
  const candidate = links.at(-1)?.href || (
    location.protocol === "http:" || location.protocol === "https:"
      ? new URL("/favicon.ico", location.origin).href
      : null
  );
  if (!candidate) return null;
  try {
    const url = new URL(candidate, document.baseURI);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
})()
""",
                return_by_value=True,
            )
        except CDPCommandException, RuntimeError:
            return None
        if result.exception_details is not None:
            return None
        value = result.result.value
        return value if isinstance(value, str) and value else None
