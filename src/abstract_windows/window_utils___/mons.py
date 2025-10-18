from __future__ import annotations
from abstract_utilities import is_number
from typing import List, Dict, Optional, Union, Callable
import threading,re,subprocess, time, shlex
import os
XRANDR_CMD     = ["xrandr"]  # or ["xrandr", "--listmonitors"] if you prefer
# Regex patterns
MONITOR_REGEX  = re.compile(
    r"""^
    (?P<name>\S+)\s+             # e.g. "DisplayPort-1-2"
    connected                     # literal word
    (?:\s+primary)?               # optional " primary"
    \s+
    (?P<width>\d+)x(?P<height>\d+)  # resolution, e.g. "2560x1440"
    \+(?P<x>\d+)\+(?P<y>\d+)        # offsets, e.g. "+0+0"
    """,
    re.VERBOSE
)
_MON_CACHE: Optional[List[Dict[str, int]]] = None
def get_mon_index(monitor_index: Union[int, str, None]) -> Optional[int]:
    if monitor_index is None:
        return None
    if isinstance(monitor_index, int):
        return monitor_index
    s = str(monitor_index)
    digits = ''.join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else None

def get_monitors():
    monitors = []
    try:
        result = subprocess.run(
            XRANDR_CMD, capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            m = MONITOR_REGEX.search(line)
            if not m:
                continue
            gd = m.groupdict()
            monitors.append({
                "name":   gd["name"],
                "x":      int(gd["x"]),
                "y":      int(gd["y"]),
                "width":  int(gd["width"]),
                "height": int(gd["height"]),
            })
    except subprocess.SubprocessError as e:
        print(f"Error running xrandr: {e}")
    return monitors

def get_monitors_fast() -> List[Dict[str, int]]:
    """
    Cache of monitor geometries via `xrandr --listmonitors`.
    """
    global _MON_CACHE
    if _MON_CACHE is not None:
        return _MON_CACHE

    out = subprocess.run(
            XRANDR_CMD, capture_output=True, text=True, check=True
        )
    mons: List[Dict[str, int]] = []

    _MON_CACHE = get_monitors()
    return _MON_CACHE
def get_monitor_geom_by_index(idx: int) -> Optional[Dict[str, int]]:
    # Reuse your get_monitors()
    mons = get_monitors()
    if idx < 0 or idx >= len(mons):
        return None
    m = mons[idx]
    return {"x": m["x"], "y": m["y"], "width": m["width"], "height": m["height"]}
def get_monitor_for_window(
    window_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None
) -> Dict[str, Union[str, int]]:
    """Determine which monitor a given window (or coordinate) is on."""

    if window_id and x is None and y is None:
        geom = get_window_geometry(window_id = window_id)
        if geom is None:
            return {}
        x, y = geom['x'], geom['y']

    if x is None or y is None:
        return {}
    for mon in get_monitors_fast():
        if mon['x'] <= x < mon['x'] + mon['width'] and \
           mon['y'] <= y < mon['y'] + mon['height']:
            return {
                'monitor_name': mon['name'],
                'monitor_details': f"{mon['width']}x{mon['height']}+{mon['x']}+{mon['y']}",
                'win_x': x,
                'win_y': y
            }
    return {}
def get_monitor_geom_by_index(idx: int) -> Optional[Dict[str, int]]:
    # Reuse your get_monitors()
    mons = get_monitors_fast()
    if idx < 0 or idx >= len(mons):
        return None
    m = mons[idx]
    return {"x": m["x"], "y": m["y"], "width": m["width"], "height": m["height"]}

def get_monitor_for_xy(x: int, y: int) -> Dict[str, Union[str, int]]:
    for mon in get_monitors_fast():
        if mon["x"] <= x < mon["x"] + mon["width"] and mon["y"] <= y < mon["y"] + mon["height"]:
            return {
                "monitor_name": mon["name"],
                "monitor_details": f'{mon["width"]}x{mon["height"]}+{mon["x"]}+{mon["y"]}',
                "win_x": x,
                "win_y": y,
            }
    return {}


def move_window_to_monitor(window_id: str, monitor_index: int) -> bool:
    geom = get_monitor_geom_by_index(monitor_index)
    if not geom:
        print(f"[abstract_windows] monitor {monitor_index} not found.")
        return False
    x, y = geom["x"], geom["y"]
    try:
        subprocess.run(
            WMCTRL_MOVE_CMD + [window_id, "-e", f"0,{x},{y},-1,-1"],
            check=True, text=True
        )
        return True
    except subprocess.SubprocessError as e:
        print(f"[abstract_windows] wmctrl move error: {e}")
        return False

