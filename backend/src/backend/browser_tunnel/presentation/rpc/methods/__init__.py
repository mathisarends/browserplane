import pyrpckit as rpc

from backend.browser_tunnel.application import Browser

from .clipboard import ClipboardMethods
from .input import InputMethods
from .navigation import NavigationMethods
from .tabs import TabMethods

BROWSER_RPC_METHODS = (
    NavigationMethods,
    InputMethods,
    ClipboardMethods,
    TabMethods,
)


def browser_rpc_methods(browser: Browser) -> tuple[rpc.RpcHandler, ...]:
    return (
        NavigationMethods(browser.navigation),
        InputMethods(browser.input),
        ClipboardMethods(browser.clipboard),
        TabMethods(browser.tabs),
    )


__all__ = ["BROWSER_RPC_METHODS", "browser_rpc_methods"]
