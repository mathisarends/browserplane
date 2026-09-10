from .clipboard import clipboard
from .input import input_methods
from .navigation import navigation
from .tabs import tabs

BROWSER_RPC_MODULES = (
    navigation,
    input_methods,
    clipboard,
    tabs,
)

__all__ = ["BROWSER_RPC_MODULES"]
