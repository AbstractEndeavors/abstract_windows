# core/process_layer.py
import os
from typing import List
from .model import UiEntity, Visibility, DisplayBackend
from .model import ProgramSignature
from .resolver_utils import get_program_signature_for_pid


def enumerate_process_apps() -> List[UiEntity]:
    entities: List[UiEntity] = []

    for pid in filter(str.isdigit, os.listdir("/proc")):
        sig = get_program_signature_for_pid(pid)
        if not sig["exe"]:
            continue

        name = os.path.basename(sig["exe"])
        entities.append(
            UiEntity(
                pid=pid,
                name=name,
                source="process",
                visibility=Visibility.PROCESS_ONLY,
                display_backend=_get_backend(),
                program=ProgramSignature(**sig),
                extra={}
            )
        )
    return entities


def _get_backend() -> DisplayBackend:
    return (
        DisplayBackend.WAYLAND
        if os.environ.get("XDG_SESSION_TYPE") == "wayland"
        else DisplayBackend.X11
    )
