import os

def _norm(p: str) -> str:
    try:
        return os.path.abspath(os.path.realpath(p))
    except Exception:
        return os.path.abspath(p)

def find_idle_window_for_file(path: str, rows: list[dict]) -> dict | None:
    """Find an open IDLE editor window that has file_path opened."""
    target = _norm(path)
    base   = os.path.basename(target)

    for w in rows:
        sig = w.get("program_signature") or {}
        args = sig.get("args") or []
        mod  = (sig.get("module") or "").lower()

        # Best: IDLE launched via -m idlelib.idle with the target path in args
        if mod == "idlelib.idle" and any(_norm(a) == target for a in args if a.endswith(".py")):
            return w

        # Fallback: window title check (IDLE usually shows "name.py - /full/path (...)" )
        title = (w.get("window_title") or "").lower()
        if base.lower() in title and os.path.dirname(target).lower() in title:
            return w
    return None
