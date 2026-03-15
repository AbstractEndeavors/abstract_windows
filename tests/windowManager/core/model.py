# core/model.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class DisplayBackend(str, Enum):
    X11 = "x11"
    WAYLAND = "wayland"
    UNKNOWN = "unknown"


class Visibility(str, Enum):
    EXACT = "exact"              # X11 window
    PARTIAL = "partial"          # compositor admits app exists
    PROCESS_ONLY = "process"     # only process-level truth
    UNAVAILABLE = "unavailable"


@dataclass
class ProgramSignature:
    pid: str
    exe: Optional[str]
    cwd: Optional[str]
    argv: Optional[str]
    args: list[str]
    script: Optional[str]
    module: Optional[str]
    kind: Optional[str]


@dataclass
class UiEntity:
    pid: str
    name: str
    source: str
    visibility: Visibility
    display_backend: DisplayBackend

    program: Optional[ProgramSignature] = None
    window_id: Optional[str] = None
    wm_class: Optional[str] = None
    window_title: Optional[str] = None
    geometry: Optional[Dict[str, int]] = None
    extra: Dict[str, Any] = None
