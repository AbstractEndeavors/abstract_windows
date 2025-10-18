from __future__ import annotations
import os, time, json, subprocess
from typing import List, Dict, Optional, Union, Any
from .monitor_utils import move_window_to_monitor, get_mon_index
# ✅ fixed import block
from .window_core import *
def _place_and_focus(w: Dict[str, Any], monitor_index: Optional[int]) -> Dict[str, Union[str, bool]]:
    wid = w.get("window_id")
    moved = True
    if wid and monitor_index is not None:
        moved = move_window_to_monitor(wid, monitor_index)
    activated = bool(wid) and activate_window(wid)
    if not activated and w.get("window_title"):
        focus_window(w["window_title"])
    return {"launched": False, "window_id": wid or "", "moved": moved, "activated": activated}

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
    while time.time() < deadline:
        time.sleep(poll_interval)
        parsed = get_all_parsed_windows()
        pid_str = str(proc.pid)
        for w in parsed:
            wid = w.get("window_id")
            if wid not in before_ids:
                if prefer_pid_match and w.get("pid") == pid_str:
                    return w
        # Fallback direct PID
        match = next((w for w in parsed if w.get("pid") == pid_str), None)
        if match:
            return match
        if title_fallback:
            match = find_window_by_title_fragments(title_fallback)
            if match:
                return match
    return None

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
    - If window is already open: focus and raise.
    - Otherwise, launch it, wait for detection, then focus it.
    """

    # ---- lock/debounce ----
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
                existing = find_window_for_script(path)
                if existing:
                    _place_and_focus(existing, get_mon_index(monitor_index))
                    return {"launched": False, "window_id": existing.get("window_id"), "moved": True, "activated": True}
        with open(lock_path, "w") as f:
            json.dump({"ts": now}, f)
    except Exception:
        pass

    # ---- 1. Check if already running ----
    existing = find_window_for_script(path)
    if existing:
        _place_and_focus(existing, get_mon_index(monitor_index))
        focus_window(existing.get("window_title", os.path.basename(path)))
        return {"launched": False, "window_id": existing.get("window_id"), "moved": True, "activated": True}

    # ---- 2. Launch new instance ----
    try:
        proc = subprocess.Popen(launch_cmd, cwd=cwd, start_new_session=True)
        print(f"[abstract_windows] launched process PID={proc.pid}: {' '.join(launch_cmd)}")
    except Exception as e:
        print(f"[abstract_windows] launch error: {e}")
        return {"launched": False, "window_id": "", "moved": False, "activated": False}

    # ---- 3. Wait for its window to appear ----
    win = get_new_window_info(
        launch_cmd, cwd,
        timeout=appear_timeout_sec,
        poll_interval=poll_interval_sec,
        prefer_pid_match=True,
        title_fallback=(match_strings or [os.path.basename(path)]),
    )

    if not win:
        print("[abstract_windows] warning: window not detected, but process launched")
        return {"launched": True, "window_id": "", "moved": False, "activated": False}

    # ---- 4. Move + focus ----
    wid = win.get("window_id", "")
    mon_idx = get_mon_index(monitor_index)
    moved = move_window_to_monitor(wid, mon_idx) if mon_idx is not None else True
    activate_window(wid)
    focus_window(win.get("window_title", os.path.basename(path)))

    return {"launched": True, "window_id": wid, "moved": moved, "activated": True}
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
