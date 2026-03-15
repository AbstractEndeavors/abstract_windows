from __future__ import annotations
import os, time, json, subprocess
from typing import List, Dict, Optional, Union, Any
from .window_utils import (  # your module
    get_windows_list, parse_window, move_window_to_monitor, activate_window,get_all_parsed_windows,
    find_window_for_script
)
from .monitor_utils import get_mon_index
# ----------------- small helpers -----------------

def get_window_ids(parsed_windows: Optional[List[Dict[str, Any]]] = None) -> set[str]:
    parsed_windows = parsed_windows or get_all_parsed_windows()
    return {w.get('window_id') for w in parsed_windows if w.get('window_id')}



def find_window_by_title_fragments(fragments: List[str]) -> Optional[Dict[str, Any]]:
    frags = [f.lower() for f in fragments]
    for w in get_all_parsed_windows():
        title = (w.get('window_title') or '').lower()
        if any(f in title for f in frags):
            return w
    return None

def _place_and_focus(w: Dict[str, Any], monitor_index: Optional[int]) -> Dict[str, Union[str, bool]]:
    wid = w.get('window_id')
    moved = True
    if wid and monitor_index is not None:
        moved = move_window_to_monitor(wid, monitor_index)
    activated = bool(wid) and activate_window(wid)
    return {"launched": False, "window_id": wid or "", "moved": moved, "activated": activated}

# ----------------- core: safe, single-instance -----------------

def get_new_window_info(
    launch_cmd: List[str],
    cwd: Optional[str],
    *,
    timeout: float = 10.0,
    poll_interval: float = 0.25,
    prefer_pid_match: bool = True,
    title_fallback: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Launch once, then wait for a new window. Don't spin; obey timeout.
    Prefer matching window by spawned PID; optionally fall back to title.
    """
    before_ids = get_window_ids()
    proc = subprocess.Popen(launch_cmd, cwd=cwd)
    deadline = time.time() + timeout

    last_seen: Optional[Dict[str, Any]] = None
    while time.time() < deadline:
        time.sleep(poll_interval)
        parsed = get_all_parsed_windows()

        # 1) Prefer exact new ID (set difference)
        for w in parsed:
            wid = w.get('window_id')
            if wid and wid not in before_ids:
                last_seen = w
                # if WM gave PID, try PID equality
                if prefer_pid_match and w.get("pid") == str(proc.pid):
                    return w

        # 2) Exact PID match (even if ID reused)
        for w in parsed:
            if w.get("pid") == str(proc.pid):
                return w

        # 3) Title fallback (helps WMs that delay PID)
        if title_fallback:
            maybe = find_window_by_title_fragments(title_fallback)
            if maybe:
                last_seen = maybe

    return last_seen  # may be None

def ensure_single_instance_or_launch(
    *,
    path: str,
    match_strings: Optional[List[str]] = None,
    monitor_index: Union[int, str, None] = 1,
    launch_cmd: List[str],
    cwd: Optional[str] = None,
    appear_timeout_sec: float = 7.0,
    poll_interval_sec: float = 0.12,
    lock_path: Optional[str] = None,
    debounce_sec: float = 0.75,
) -> Dict[str, Union[str, bool]]:
    """
    Safe single-instance:
      1) If a window for this script is open -> place & focus.
      2) Else launch once; wait (with timeout) for its window; place & focus.

    Includes:
      - lock/debounce to avoid double-click storms
      - no infinite loops
    """
    # ---- debounce: stop click-storms from spawning multiple processes ----
    if lock_path is None:
        lock_path = os.path.expanduser("~/.cache/abstract-ide/launch.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)

    now = time.time()
    try:
        if os.path.exists(lock_path):
            with open(lock_path, "r") as f:
                data = json.load(f)
            last = float(data.get("ts", 0))
            if now - last < debounce_sec:
                # Another launcher just ran; try to bring to front instead of relaunching.
                existing = find_window_for_script(path)
                if existing:
                    return _place_and_focus(existing, get_mon_index(monitor_index))
        # update stamp
        with open(lock_path, "w") as f:
            json.dump({"ts": now}, f)
    except Exception:
        pass  # don't fail launching because of lock i/o

    # ---- 1) check for existing window by exact source signature ----
    existing = find_window_for_script(path)
    if existing:
        return _place_and_focus(existing, get_mon_index(monitor_index))

    # ---- 2) launch once, then locate safely (PID / new ID / title fallback) ----
    win = get_new_window_info(
        launch_cmd, cwd,
        timeout=appear_timeout_sec,
        poll_interval=poll_interval_sec,
        prefer_pid_match=True,
        title_fallback=(match_strings or []),
    )
    if not win:
        return {"launched": True, "window_id": "", "moved": False, "activated": False}

    wid = win.get("window_id") or ""
    moved = True
    mon_idx = get_mon_index(monitor_index)
    if mon_idx is not None:
        moved = move_window_to_monitor(wid, mon_idx)
    activated = activate_window(wid)
    return {"launched": True, "window_id": wid, "moved": moved, "activated": activated}

# ----------------- convenience: launch python with conda -----------------

def launch_python_conda_script(
    path: str,
    *,
    env_name: str = "base",
    conda_exe: str = "/home/computron/miniconda/bin/conda",
    display: str = ":0",
    monitor_index: Union[int, str, None] = 1,
) -> Dict[str, Union[str, bool]]:
    """
    Launch a python script via `conda run` (no shell sourcing), single-instance & safe.
    """
    script_abs = os.path.abspath(path)
    workdir = os.path.dirname(script_abs)

    launch_cmd = [
        conda_exe, "run", "-n", env_name, "--no-capture-output",
        "env", f"DISPLAY={display}",
        "python", script_abs,
    ]

    match_titles = [os.path.basename(script_abs)]  # light fallback
    return ensure_single_instance_or_launch(
        path=script_abs,
        match_strings=match_titles,
        monitor_index=monitor_index,   # ← integer like 1 (NOT DISPLAY)
        launch_cmd=launch_cmd,
        cwd=workdir,
        appear_timeout_sec=8.0,
        poll_interval_sec=0.15,
    )
def edit_python_conda_script(
    path: str,
    *,
    env_name: str = "base",
    conda_exe: str = "/home/computron/miniconda/bin/conda",
    display: str = ":0",
    monitor_index: Union[int, str, None] = 1,
) -> Dict[str, Union[str, bool]]:
    """
    Open the given Python file in IDLE (edit mode) using the given Conda env,
    but if that file is already open in any IDLE editor window,
    just focus that window instead of reopening it.
    """

    from .idle_utils import find_idle_window_for_file  # ensures edit-window match
    script_abs = os.path.abspath(path)
    workdir = os.path.dirname(script_abs)

    # collect all currently open windows
    parsed = get_all_parsed_windows(with_signature=True)
    existing = find_idle_window_for_file(script_abs, parsed)

    if existing:
        # ✅ bring to front instead of reopening
        wid = existing.get("window_id")
        print(f"[abstract_windows] focusing existing IDLE window for {script_abs}")
        return _place_and_focus(existing, get_mon_index(monitor_index))

    # --- no existing IDLE window found; open it once ---
    match_titles = [os.path.basename(script_abs), "IDLE"]

    launch_cmd = [
        conda_exe, "run", "-n", env_name, "--no-capture-output",
        "env", f"DISPLAY={display}",
        "python", "-m", "idlelib.idle", "-e", script_abs,
    ]

    print(f"[abstract_windows] launching IDLE edit for {script_abs}")
    return ensure_single_instance_or_launch(
        path=script_abs,
        match_strings=match_titles,
        monitor_index=monitor_index,
        launch_cmd=launch_cmd,
        cwd=workdir,
        appear_timeout_sec=10.0,
        poll_interval_sec=0.25,
    )

