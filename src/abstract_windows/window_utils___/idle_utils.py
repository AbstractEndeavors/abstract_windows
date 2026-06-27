import os

def _norm(p: str) -> str:
    try:
        return os.path.abspath(os.path.realpath(p))
    except Exception:
        return os.path.abspath(p)

def find_idle_window_for_file(path: str, rows: list[dict]) -> dict | None:
    """Find an open IDLE editor window that has file_path opened."""
    target = _norm(path)
    base = os.path.basename(target)

    for w in rows:
        if not isinstance(w, dict):
            continue
        sig = w.get("program_signature") or {}
        if not isinstance(sig, dict):
            continue
        args = sig.get("args") or []
        if not isinstance(args, (list, tuple)):
            continue
        mod = (sig.get("module") or "").lower()

        # Prefer exact match via idlelib.idle
        for a in args:
            if not isinstance(a, str):
                continue
            if a.endswith(".py") and _norm(a) == target and mod == "idlelib.idle":
                return w

        # Fallback: check title text
        title = (w.get("window_title") or "")
        if isinstance(title, str) and base.lower() in title.lower() and \
           os.path.dirname(target).lower() in title.lower():
            return w
    return None
