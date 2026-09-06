import asyncio
import logging
from contextlib import suppress

from cdpify import CDPSession
from cdpify.domains.runtime.events import BindingCalledEvent, RuntimeEvent
from cdpify.exceptions import CDPCommandException

from backend.features.browser_tunnel.application import CursorChanged, CursorStyle
from backend.features.browser_tunnel.infrastructure.events.stream import PublishEvent

logger = logging.getLogger(__name__)

_BINDING_NAME = "__browserTunnelCursor"
_ISOLATED_WORLD = "browsertunnel:cursor"

_OBSERVER_SOURCE = """
(() => {
  const report = window.__BINDING__;
  if (typeof report !== "function") return;

  const range = document.createRange();
  const overText = (element, x, y) => {
    for (const node of element.childNodes) {
      if (node.nodeType !== Node.TEXT_NODE || !node.nodeValue.trim()) continue;
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
          return true;
        }
      }
    }
    return false;
  };

  const resolve = (x, y) => {
    const hit = document.elementFromPoint(x, y);
    if (!hit) return "default";

    for (let element = hit; element; element = element.parentElement) {
      const cursor = getComputedStyle(element).cursor;
      if (cursor && cursor !== "auto") return cursor;
    }
    return hit.isContentEditable || overText(hit, x, y) ? "text" : "default";
  };

  if (globalThis.__browserTunnelCursorObserver) {
    removeEventListener("mousemove", globalThis.__browserTunnelCursorObserver, true);
  }
  globalThis.__browserTunnelCursorObserver =
    (event) => report(resolve(event.clientX, event.clientY));
  addEventListener("mousemove", globalThis.__browserTunnelCursorObserver,
    { capture: true, passive: true });
})();
""".replace("__BINDING__", _BINDING_NAME)


class CursorEventBridge:
    def __init__(self, publish: PublishEvent) -> None:
        self._publish = publish
        self._task: asyncio.Task[None] | None = None
        self._target_id: str | None = None
        self._cursor = CursorStyle.DEFAULT
        self._session: CDPSession | None = None
        self._script_id: str | None = None

    async def start(self, session: CDPSession, target_id: str) -> None:
        await self.stop()
        self._session = session
        self._target_id = target_id
        self._cursor = CursorStyle.DEFAULT
        await session.runtime.enable()
        await session.runtime.add_binding(
            name=_BINDING_NAME, execution_context_name=_ISOLATED_WORLD
        )
        script = await session.page.add_script_to_evaluate_on_new_document(
            source=_OBSERVER_SOURCE,
            world_name=_ISOLATED_WORLD,
            run_immediately=True,
        )
        self._script_id = script.identifier
        self._task = asyncio.create_task(self._pump(session), name="active-page:cursor")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        self._target_id = None
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        session, self._session = self._session, None
        script_id, self._script_id = self._script_id, None
        if session is not None:
            with suppress(CDPCommandException):
                if script_id is not None:
                    await session.page.remove_script_to_evaluate_on_new_document(
                        identifier=script_id
                    )
                await session.runtime.remove_binding(name=_BINDING_NAME)

    @property
    def cursor(self) -> CursorStyle:
        return self._cursor

    async def _pump(self, session: CDPSession) -> None:
        try:
            async for event in session.listen(
                RuntimeEvent.BINDING_CALLED, BindingCalledEvent
            ):
                if event.name == _BINDING_NAME:
                    await self._dispatch(CursorStyle.parse(event.payload))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("CDP cursor observer stopped unexpectedly")

    async def _dispatch(self, cursor: CursorStyle) -> None:
        target_id = self._target_id
        if target_id is None or cursor == self._cursor:
            return
        self._cursor = cursor
        self._publish(CursorChanged(target_id, cursor))
