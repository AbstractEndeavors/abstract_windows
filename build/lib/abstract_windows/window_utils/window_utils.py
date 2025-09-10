from __future__ import annotations
from typing import List, Dict, Optional, Union, Callable
import threading,re,subprocess, time, shlex
from Xlib import X, display
from Xlib.ext import randr
from difflib import get_close_matches

XRANDR_CMD     = ["xrandr"]  # or ["xrandr", "--listmonitors"] if you prefer
WMCTRL_LIST_CMD = ['wmctrl', '-l', '-p']
WMCTRL_MOVE_CMD = ['wmctrl', '-i', '-r']
XDOTOOL_GEOMETRY_CMD = ['xdotool', 'getwindowgeometry']

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

POSITION_REGEX = re.compile(r'Position:\s+(\d+),(\d+)')
GEOMETRY_REGEX = re.compile(r'Geometry:\s+(\d+)x(\d+)')






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



def get_strings_in_string(string,strings):
    for comp_string in strings:
        if comp_string.lower() in string.lower():
            return True
    return False
def get_windows_list():
    result = subprocess.run(
                WMCTRL_LIST_CMD, capture_output=True, text=True, check=True
            )
    windows = result.stdout.splitlines()
    return windows
def get_filters(
    windows: List[str],
    find_window_id: Optional[str] = None,
    find_desktop: Optional[str] = None,
    find_pid: Optional[str] = None,
    find_host: Optional[str] = None,
    find_window_title: Optional[str] = None
):
    filters = {k: v for k, v in {
        'window_id': find_window_id,
        'desktop': find_desktop,
        'pid': find_pid,
        'host': find_host,
        'window_title': find_window_title
    }.items() if v is not None}
    return filters


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
    for mon in get_monitors():
        if mon['x'] <= x < mon['x'] + mon['width'] and \
           mon['y'] <= y < mon['y'] + mon['height']:
            return {
                'monitor_name': mon['name'],
                'monitor_details': f"{mon['width']}x{mon['height']}+{mon['x']}+{mon['y']}",
                'win_x': x,
                'win_y': y
            }
    return {}
def parse_window(window):
    parts = window.split(None, 4)
    if len(parts) >= 5:
        win_id, desktop, pid, host, title = parts
        monitor_info = get_monitor_for_window(window_id=win_id)
        window_geometry = get_window_geometry(window_id=win_id)
        info = {
            'window_id': win_id, 'desktop': desktop, 'pid': pid,
            'host': host, 'window_title': title,'monitor_info':monitor_info,
            'window_geometry':window_geometry
        }
        
        info.update(monitor_info)
        return info
# --- FIX a bug in your code: 'parsed_window' var wasn't defined in filter_window() ---
def filter_window(info, filters={}):
    if not filters:
        return info
    # only compare keys that exist
    for k, v in filters.items():
        if info.get(k) != v:
            return None
    return info

def parse_windows(windows,filters={}):
    parsed_windows = []
    for window in windows:
        parsed_window = parse_window(window)
        filtered_window = filter_window(parsed_window,filters=filters)
        if filtered_window:
            return filtered_window
        if parsed_window:
            parsed_windows.append(parsed_window)
    return parsed_windows
def get_window_items(
    windows: List[str],
    find_window_id: Optional[str] = None,
    find_desktop: Optional[str] = None,
    find_pid: Optional[str] = None,
    find_host: Optional[str] = None,
    find_window_title: Optional[str] = None
) -> Union[Dict[str, str], List[Dict[str, str]]]:
    """Parse `wmctrl -l -p` output, optionally filtering."""
    filters = get_filters(
        windows=windows,
        find_window_id= find_window_id,
        find_desktop= find_desktop,
        find_pid= find_pid,
        find_host= find_host,
        find_window_title= find_window_title
        )
    parsed = parse_windows(windows,filters)
    return parsed
def get_window_geometry(window_id: str) -> Optional[Dict[str, int]]:
    """Get window position (x, y) and size (width, height) using xdotool."""
    try:
        result = subprocess.run(
            XDOTOOL_GEOMETRY_CMD + [window_id],
            capture_output=True, text=True, check=True
        )
        pos_m = POSITION_REGEX.search(result.stdout)
        size_m = GEOMETRY_REGEX.search(result.stdout)
        if pos_m and size_m:
            return {
                'x': int(pos_m.group(1)),
                'y': int(pos_m.group(2)),
                'width': int(size_m.group(1)),
                'height': int(size_m.group(2))
            }
        return None
    except subprocess.SubprocessError as e:
        print(f"Error getting geometry: {e}")
        return None
def find_window_by_title_contains(substrings: List[str]) -> Optional[Dict[str, str]]:
    """Return the first window whose title contains ANY of the substrings (case-insensitive)."""
    windows = get_windows_list()
    parsed = parse_windows(windows, filters={})  # returns list
    if isinstance(parsed, dict):  # guard if single dict ever returned
        parsed = [parsed]
    for w in parsed:
        title = w.get('window_title', '') or ''
        for s in substrings:
            if s.lower() in title.lower():
                return w
    return None

def get_monitor_geom_by_index(idx: int) -> Optional[Dict[str, int]]:
    # Reuse your get_monitors()
    mons = get_monitors()
    if idx < 0 or idx >= len(mons):
        return None
    m = mons[idx]
    return {"x": m["x"], "y": m["y"], "width": m["width"], "height": m["height"]}

def move_window_to_monitor(window_id: str, monitor_index: int) -> bool:
    geom = get_monitor_geom_by_index(monitor_index)
    if not geom:
        print(f"[abstract_windows] monitor {monitor_index} not found.")
        return False
    x, y = geom["x"], geom["y"]
    try:
        subprocess.run(['wmctrl', '-i', '-r', window_id, '-e', f'0,{x},{y},-1,-1'],
                       check=True, text=True)
        return True
    except subprocess.SubprocessError as e:
        print(f"[abstract_windows] wmctrl move error: {e}")
        return False

def activate_window(window_id: str) -> bool:
    try:
        subprocess.run(['wmctrl', '-i', '-a', window_id], check=True, text=True)
        return True
    except subprocess.SubprocessError as e:
        print(f"[abstract_windows] wmctrl activate error: {e}")
        return False

def get_parsed_windows():
    windows = get_windows_list()
    filters = get_filters(windows=windows)
    parsed_windows = parse_windows(windows=windows,filters=filters)
    return parsed_windows
