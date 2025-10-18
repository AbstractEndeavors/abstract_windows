from __future__ import annotations
from typing import List, Dict, Optional, Union
import subprocess, re, os

XRANDR_CMD = ["xrandr"]
WMCTRL_MOVE_CMD = ["wmctrl", "-i", "-r"]

# Monitor info cache
_MON_CACHE: Optional[List[Dict[str, int]]] = None

MONITOR_REGEX = re.compile(
    r"""^
    (?P<name>\S+)\s+connected(?:\s+primary)?\s+
    (?P<width>\d+)x(?P<height>\d+)\+(?P<x>\d+)\+(?P<y>\d+)
    """,
    re.VERBOSE
)

def _run_xrandr() -> str:
    try:
        return subprocess.check_output(XRANDR_CMD, text=True, errors="ignore")
    except Exception:
        return ""

def _parse_xrandr_output(out: str) -> List[Dict[str, int]]:
    mons = []
    for line in out.splitlines():
        m = MONITOR_REGEX.search(line)
        if not m:
            continue
        gd = m.groupdict()
        mons.append({k: int(v) if v.isdigit() else v for k, v in gd.items()})
    return mons

def get_monitors() -> List[Dict[str, int]]:
    """Fetch all connected monitors (no cache)."""
    return _parse_xrandr_output(_run_xrandr())

def get_monitors_fast() -> List[Dict[str, int]]:
    """Cached version of get_monitors()."""
    global _MON_CACHE
    if _MON_CACHE is None:
        _MON_CACHE = get_monitors()
    return _MON_CACHE

def get_monitor_geom_by_index(idx: int) -> Optional[Dict[str, int]]:
    mons = get_monitors_fast()
    if 0 <= idx < len(mons):
        return mons[idx]
    return None

def get_monitor_for_xy(x: int, y: int) -> Dict[str, Union[str, int]]:
    """Return which monitor contains coordinates (x, y)."""
    for mon in get_monitors_fast():
        if mon["x"] <= x < mon["x"] + mon["width"] and mon["y"] <= y < mon["y"] + mon["height"]:
            return {
                "monitor_name": mon["name"],
                "monitor_details": f'{mon["width"]}x{mon["height"]}+{mon["x"]}+{mon["y"]}',
                "win_x": x,
                "win_y": y,
            }
    return {}

def get_mon_index(monitor_index: Union[int, str, None]) -> Optional[int]:
    if monitor_index is None:
        return None
    if isinstance(monitor_index, int):
        return monitor_index
    digits = "".join(ch for ch in str(monitor_index) if ch.isdigit())
    return int(digits) if digits else None

def move_window_to_monitor(window_id: str, monitor_index: int) -> bool:
    geom = get_monitor_geom_by_index(monitor_index)
    if not geom:
        print(f"[abstract_windows] monitor {monitor_index} not found.")
        return False
    try:
        subprocess.run(
            WMCTRL_MOVE_CMD + [window_id, "-e", f"0,{geom['x']},{geom['y']},-1,-1"],
            check=True, text=True
        )
        return True
    except subprocess.SubprocessError as e:
        print(f"[abstract_windows] wmctrl move error: {e}")
        return False


# -------------------------
# enrich + parsing helpers
# -------------------------
def _enrich_row(row: Dict[str, str], *, with_signature: bool = False, with_geometry: bool = False) -> Dict[str, Any]:
    """Add optional fields lazily to a wmctrl row."""
    out: Dict[str, Any] = dict(row)
    if with_signature and row.get("pid"):
        out["program_signature"] = get_program_signature_for_pid(row["pid"])
    if with_geometry and row.get("window_id"):
        geom = get_window_geometry(row["window_id"])
        if geom:
            out["window_geometry"] = geom
            # map to a monitor if possible
            mon = get_monitor_for_xy(geom["x"], geom["y"])
            if mon:
                out.update(mon)
    return out

def get_all_parsed_windows(*, with_signature: bool = True, with_geometry: bool = False) -> List[Dict[str, Any]]:
    rows = _wmctrl_snapshot()
    return [_enrich_row(r, with_signature=with_signature, with_geometry=with_geometry) for r in rows]

# Backwards compatibility: your old functions
def get_windows_list() -> List[str]:
    """Kept for compatibility; prefer _wmctrl_snapshot() instead."""
    # Reconstruct a string like wmctrl -l -p (without class); only used if needed
    out = subprocess.check_output(["wmctrl", "-l", "-p"], text=True, errors="ignore")
    return out.splitlines()

def parse_window(window: str) -> Optional[Dict[str, Any]]:
    """Legacy parser for wmctrl -l -p lines; prefer get_all_parsed_windows()."""
    parts = window.split(None, 4)
    if len(parts) < 5:
        return None
    win_id, desktop, pid, host, title = parts
    row = {
        "window_id": win_id, "desktop": desktop, "pid": pid, "host": host,
        "wm_class": "", "window_title": title
    }
    # lazily enrich with signature; geometry only on demand
    return _enrich_row(row, with_signature=True, with_geometry=False)
