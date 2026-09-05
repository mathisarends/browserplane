import json

from data_plane.features.browser_state.application.models import BrowserTabState

CAPTURE_EXPRESSION = """
(() => {
    let sessionStorage = [];
    try {
        sessionStorage = Array.from(
            {length: window.sessionStorage.length},
            (_, index) => {
                const name = window.sessionStorage.key(index);
                return {name, value: window.sessionStorage.getItem(name)};
            },
        ).filter((item) => item.name !== null);
    } catch (error) {}

    return {
        url: window.location.href,
        scroll: {
            x: Math.max(0, Math.round(window.scrollX)),
            y: Math.max(0, Math.round(window.scrollY)),
        },
        session_storage: sessionStorage,
        visible: document.visibilityState === "visible",
    };
})()
"""


def build_restore_script(tab: BrowserTabState, origin: str) -> str:
    """Build the script that restores a tab's sessionStorage and scroll.

    It runs on every new document of the tab, so it checks the origin first:
    a redirect must not write another site's sessionStorage. The caller
    removes it again once the tab has loaded.
    """
    writes = "\n        ".join(
        f"window.sessionStorage.setItem({json.dumps(item.name)}, "
        f"{json.dumps(item.value)});"
        for item in tab.session_storage
    )
    return f"""
(() => {{
    if (window.location.origin !== {json.dumps(origin)}) return;
    try {{
        window.sessionStorage.clear();
        {writes}
    }} catch (error) {{}}

    const restoreScroll = () => window.requestAnimationFrame(
        () => window.requestAnimationFrame(
            () => window.scrollTo({tab.scroll.x}, {tab.scroll.y}),
        ),
    );
    if (document.readyState === "complete") {{
        restoreScroll();
    }} else {{
        window.addEventListener("load", restoreScroll, {{once: true}});
    }}
}})();
"""
