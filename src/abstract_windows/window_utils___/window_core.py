from __future__ import annotations
from typing import List, Dict, Optional, Any
import subprocess, os, platform, time, re
from contextlib import suppress

WMCTRL_LIST_CMD = ["wmctrl", "-lx", "-p"]

# Cached wmctrl results (avoid repeated subprocess hits)
_WMCTRL_CACHE = {"t": 0.0, "rows": []}


# ----------------------------
# /proc helpers (Linux only)
# ----------------------------
def _readlink_safe(path: str) -> Optional[str]:
    with suppress(Exception):
        return os.readlink(path)
    return None

def get_proc_exe(pid: str | int) -> Optional[str]:
    return _readlink_safe(f"/proc/{pid}/exe")

def get_proc_cwd(pid: str | int) -> Optional[str]:
    return _readlink_safe(f"/proc/{pid}/cwd")

def get_proc_cmdline(pid: str | int) -> List[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read().split(b"\x00")
        return [x.decode("utf-8", "replace") for x in raw if x]
    except Exception:
        return []


# ----------------------------
# Window Snapshot + Enrichment
# ----------------------------
def _wmctrl_snapshot() -> List[Dict[str, str]]:
    """Returns parsed wmctrl -lx -p output with caching (0.5s TTL)."""
    now = time.time()
    if now - _WMCTRL_CACHE["t"] < 0.5:
        return _WMCTRL_CACHE["rows"]

    try:
        out = subprocess.check_output(WMCTRL_LIST_CMD, text=True, errors="ignore")
    except subprocess.SubprocessError:
        return []

    rows = []
    for line in out.splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6:
            wid, desk, pid, host, wmclass, title = parts
            rows.append({
                "window_id": wid,
                "desktop": desk,
                "pid": pid,
                "host": host,
                "wm_class": wmclass,
                "window_title": title,
            })
    _WMCTRL_CACHE.update({"t": now, "rows": rows})
    return rows


# ----------------------------
# Focusing Windows (cross-platform)
# ----------------------------
def _focus_linux(title_substring: str) -> bool:
    """Try to focus a window by title on Linux (supports wmctrl, xdotool, labwc)."""
    title = title_substring.lower()
    # wmctrl path
    try:
        windows = subprocess.check_output(["wmctrl", "-l"], text=True, errors="ignore")
        for line in windows.splitlines():
            if title in line.lower():
                win_id = line.split()[0]
                subprocess.run(["wmctrl", "-i", "-a", win_id])
                return True
    except Exception:
        pass
    # xdotool fallback
    with suppress(Exception):
        subprocess.run(["xdotool", "search", "--name", title_substring, "windowactivate"])
        return True
    # labwc fallback
    if os.environ.get("XDG_SESSION_DESKTOP", "").lower().startswith("labwc"):
        with suppress(Exception):
            subprocess.run(["labwc-client", "focus", title_substring])
            return True
    return False


def _focus_macos(app_or_title: str) -> bool:
    """Focus a macOS window by app name or title."""
    with suppress(Exception):
        subprocess.run(["osascript", "-e", f'tell application "{app_or_title}" to activate'])
        return True
    return False


def _focus_windows(title_substring: str) -> bool:
    """Focus a window by title using pygetwindow on Windows."""
    with suppress(Exception):
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title_substring)
        if wins:
            win = wins[0]
            win.restore()
            win.activate()
            return True
    return False


def focus_window(title_substring: str) -> bool:
    """Cross-platform focus API."""
    system = platform.system()
    if system == "Linux":
        return _focus_linux(title_substring)
    elif system == "Darwin":
        return _focus_macos(title_substring)
    elif system == "Windows":
        return _focus_windows(title_substring)
    return False


# ----------------------------
# Activation (by window_id)
# ----------------------------
def activate_window(window_id: str) -> bool:
    """Activate a specific window by ID (Linux/X11 only)."""
    try:
        subprocess.run(["wmctrl", "-i", "-a", window_id], check=True, text=True)
        return True
    except subprocess.SubprocessError:
        return False

def guess_python_entry_from_cmdline(args: List[str], cwd: Optional[str]) -> Dict[str, Optional[str]]:
    script_path = None
    module = None
    entry_kind = None

    if not args:
        return {"script_path": None, "module": None, "entry_kind": None, "args": []}

    i = 1
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-m" and i + 1 < len(args):
            module = args[i + 1]
            entry_kind = "module"
            break
        if args[i] == "-c":
            entry_kind = "inline"
            break
        i += 1

    # 🔍 NEW: scan the remainder of args for a .py file
    for a in args[i + 1:]:
        if a.endswith(".py"):
            script_path = os.path.normpath(os.path.join(cwd, a)) if cwd and not os.path.isabs(a) else a
            break

    if entry_kind is None and i < len(args):
        cand = args[i]
        cand_abs = os.path.normpath(os.path.join(cwd, cand)) if cwd and not os.path.isabs(cand) else cand
        if os.path.splitext(cand_abs)[1] in (".py", ".pyw", ""):
            script_path = cand_abs
            entry_kind = "script"

    return {
        "script_path": script_path,
        "module": module,
        "entry_kind": entry_kind,
        "args": args,
    }


# ----------------------------
# Finders
# ----------------------------
def find_window_by_title_contains(
    substrings: List[str],
    rows: Optional[List[Dict[str, str]]] = None
) -> Optional[Dict[str, Any]]:
    rows = rows or _wmctrl_snapshot()
    subs_l = [s.lower() for s in substrings]
    for r in rows:
        title = (r.get("window_title") or "").lower()
        if any(s in title for s in subs_l):
            return r
    return None
def find_window_for_script(script_path: str, rows: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
    script_abs = os.path.abspath(script_path)
    
    rows = rows or _wmctrl_snapshot()
    for r in rows:
        pid = r.get("pid")
        if not pid:
            continue
        sig = get_program_signature_for_pid(pid)
        if sig.get("script") == script_abs:
            out = dict(r)
            out["program_signature"] = sig
            return out
    return None
def get_program_signature_for_pid(pid: Union[str, int]) -> Dict[str, Optional[str]]:
    exe = get_proc_exe(pid)
    cwd = get_proc_cwd(pid)
    argv = get_proc_cmdline(pid)
    py   = guess_python_entry_from_cmdline(argv, cwd) or {}
    return {
        'pid': str(pid),
        'exe': exe,
        'cwd': cwd,
        'argv': ' '.join(argv) if argv else None,
        'args': py.get('args') or [],          # <--- add this
        'script': py.get('script_path'),
        'module': py.get('module'),
        'kind': py.get('entry_kind'),
    }

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
