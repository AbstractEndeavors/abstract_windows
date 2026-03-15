import os

def _norm(p: str) -> str:
    try:
        return os.path.abspath(os.path.realpath(p))
    except Exception:
        return os.path.abspath(p)

def find_idle_window_for_file(path: str, rows: list[dict]) -> dict | None:
    target = _norm(path)
    base   = os.path.basename(target)

    for w in rows:
        if not isinstance(w, dict):
            continue
        sig = w.get("program_signature") or {}
        if not isinstance(sig, dict):
            sig = {}
        args = sig.get("args") or []
        if not isinstance(args, (list, tuple)):
            args = []
        mod  = (sig.get("module") or "").lower()

        # Best case: IDLE via -m idlelib.idle with the exact file arg
        for a in args:
            try:
                if a.endswith(".py") and _norm(a) == target and mod == "idlelib.idle":
                    return w
            except Exception:
                pass

        # Fallback: window title heuristic
        title = (w.get("window_title") or "")
        if isinstance(title, str) and base.lower() in title.lower() and \
           os.path.dirname(target).lower() in title.lower():
            return w

    return None
