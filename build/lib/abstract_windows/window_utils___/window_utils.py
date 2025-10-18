from __future__ import annotations
from typing import List, Dict, Optional, Union, Callable, Any, Tuple
import os, re, time, subprocess
from .monitor_utils import *
from contextlib import suppress
# -------------------------
# /proc helpers (for signature)
# -------------------------
def _readlink_safe(path: str) -> Optional[str]:
    try:
        return os.readlink(path)
    except Exception:
        return None

def get_proc_exe(pid: Union[str, int]) -> Optional[str]:
    return _readlink_safe(f"/proc/{pid}/exe")

def get_proc_cwd(pid: Union[str, int]) -> Optional[str]:
    return _readlink_safe(f"/proc/{pid}/cwd")


def get_proc_cmdline(pid: Union[str, int]) -> List[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read().split(b"\x00")
        return [x.decode("utf-8", "replace") for x in raw if x]
    except Exception:
        return []


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
# wmctrl snapshot (fast)
# -------------------------
def _wmctrl_snapshot() -> List[Dict[str, str]]:
    """
    Single fast call: returns rows with id/desk/pid/host/class/title.
    We enrich lazily later.
    """
    try:
        out = subprocess.check_output(WMCTRL_LIST_CMD, text=True, errors="ignore")
    except subprocess.SubprocessError:
        return []
    rows: List[Dict[str, str]] = []
    for line in out.splitlines():
        # wmctrl -lx -p columns: ID DESK PID HOST WM_CLASS TITLE
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        wid, desk, pid, host, wmclass, title = parts
        rows.append({
            "window_id": wid,
            "desktop": desk,
            "pid": pid,
            "host": host,
            "wm_class": wmclass,     # e.g. "python3.Idle"
            "window_title": title,
        })
    return rows




# -------------------------
# actions
# -------------------------

def activate_window(window_id: str) -> bool:
    try:
        subprocess.run(['wmctrl', '-i', '-a', window_id], check=True, text=True)
        return True
    except subprocess.SubprocessError:
        return False

# -------------------------
# matchers (fast paths)
# -------------------------
def find_window_by_title_contains(substrings: List[str], rows: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
    rows = rows or _wmctrl_snapshot()
    subs_l = [s.lower() for s in substrings]
    for r in rows:
        title = (r.get("window_title") or "").lower()
        if any(s in title for s in subs_l):
            return _enrich_row(r, with_signature=True, with_geometry=False)
    return None

def find_window_by_class(wm_class: str, rows: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
    rows = rows or _wmctrl_snapshot()
    for r in rows:
        if r.get("wm_class") == wm_class:
            return _enrich_row(r, with_signature=True, with_geometry=False)
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

def windows_matching_source(
    *,
    script_abs: Optional[str] = None,
    module: Optional[str] = None,
    exe_startswith: Optional[str] = None,
    cwd_abs: Optional[str] = None,
) -> List[Dict[str, Any]]:
    rows = _wmctrl_snapshot()
    matches: List[Dict[str, Any]] = []
    for r in rows:
        pid = r.get("pid")
        if not pid:
            continue
        sig = get_program_signature_for_pid(pid)
        ok = True
        if script_abs is not None and sig.get("script") != script_abs:
            ok = False
        if module is not None and sig.get("module") != module:
            ok = False
        if cwd_abs is not None and sig.get("cwd") != cwd_abs:
            ok = False
        if exe_startswith is not None:
            ex = sig.get("exe") or ""
            if not ex.startswith(exe_startswith):
                ok = False
        if ok:
            out = dict(r)
            out["program_signature"] = sig
            matches.append(out)
    return matches

# -------------------------
# convenience (what you used before)
# -------------------------
def get_parsed_windows() -> List[Dict[str, Any]]:
    """Compatibility shim for callers expecting a list of enriched windows."""
    return get_all_parsed_windows(with_signature=True, with_geometry=False)

