# api.py
from .core.resolver import resolve_ui_state
from .core.model import UiEntity


def get_ui_state() -> list[UiEntity]:
    """
    Authoritative system UI state.
    Window-accurate on X11, app-accurate on Wayland.
    """
    return resolve_ui_state()


def find_app(name: str) -> list[UiEntity]:
    name = name.lower()
    return [e for e in resolve_ui_state() if name in e.name.lower()]
