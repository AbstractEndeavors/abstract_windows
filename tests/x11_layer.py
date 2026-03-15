# core/x11_layer.py
from typing import List
from .model import UiEntity, Visibility, DisplayBackend
from .resolver_utils import (
    wmctrl_snapshot,
    get_program_signature_for_pid,
    get_window_geometry,
)


def enumerate_x11_windows() -> List[UiEntity]:
    rows = wmctrl_snapshot()
    entities: List[UiEntity] = []

    for r in rows:
        pid = r.get("pid")
        if not pid or pid == "0":
            continue

        sig = get_program_signature_for_pid(pid)
        geom = get_window_geometry(r["window_id"])

        entities.append(
            UiEntity(
                pid=pid,
                name=r.get("wm_class") or "unknown",
                source="x11",
                visibility=Visibility.EXACT,
                display_backend=DisplayBackend.X11,
                program=sig and ProgramSignature(**sig),
                window_id=r["window_id"],
                wm_class=r.get("wm_class"),
                window_title=r.get("window_title"),
                geometry=geom,
                extra={}
            )
        )

    return entities
