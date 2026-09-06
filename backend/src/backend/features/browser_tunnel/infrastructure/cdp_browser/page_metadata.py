from cdpify.exceptions import CDPCommandException

from backend.features.browser_tunnel.application import BrowserPageMetadata
from backend.features.browser_tunnel.infrastructure.cdp_browser.active_target import (
    ActiveTarget,
)


class CdpPageMetadata(BrowserPageMetadata):
    """Read page metadata through the currently mirrored CDP target."""

    def __init__(self, target: ActiveTarget) -> None:
        self._target = target

    async def favicon_url(self) -> str | None:
        try:
            result = await self._target.session().runtime.evaluate(
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
