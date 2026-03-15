# core/resolver.py
from typing import List, Dict
from .model import UiEntity, Visibility, DisplayBackend
from .process_layer import enumerate_process_apps
from .x11_layer import enumerate_x11_windows


def resolve_ui_state() -> List[UiEntity]:
    processes = enumerate_process_apps()
    x11_windows = enumerate_x11_windows()

    by_pid: Dict[str, UiEntity] = {}

    # First: process truth
    for p in processes:
        by_pid[p.pid] = p

    # Second: overlay X11 precision
    for w in x11_windows:
        by_pid[w.pid] = w  # replaces process-only with exact

    return list(by_pid.values())
