import os
from .window_utils import *
from abstract_utilities import best_match,is_number
def get_window_best_match(windows_list=None,match_strings=[]):
    windows_list = windows_list or get_windows_list()
    b_match = best_match(windows_list,terms=match_strings)
    if b_match and isinstance(b_match,dict):
        return parse_window(b_match.get('value'))
def get_mon_index(monitor_index):
    mon_index = ''
    if not is_number(monitor_index):
        for char in str(monitor_index):
            if is_number(char):
                mon_index+=char
    mon_index = mon_index or monitor_index
    if is_number(mon_index):
        mon_index = int(mon_index)
    return mon_index
def get_all_parsed_windows(windows=None):
    windows = windows or get_windows_list()
    for i,window in enumerate(windows):
        windows[i] = parse_window(window)
    return windows
def get_all_window_ids(windows=None):
    windows = get_all_parsed_windows(windows=windows)
    return [win_id.get('window_id') for win_id in windows]
def filter_win_list(window_ids):
    win_list_new = get_all_parsed_windows()
    return [win for win in win_list_new if win.get('window_id') not in window_ids]
def get_new_window_info(launch_cmd, cwd, match_strings, timeout=10, poll_interval=0.25):
    proc = subprocess.Popen(launch_cmd, cwd=cwd)
    deadline = time.time() + timeout

    while time.time() < deadline:
        time.sleep(poll_interval)
        for w in get_all_parsed_windows():
            if str(proc.pid) == w.get("pid"):
                return w
    return None
def find_window_for_script(script_path: str) -> Optional[Dict[str, Any]]:
    for w in get_all_parsed_windows():
        sig = w.get("program_signature") or {}
        if sig.get("script") == os.path.abspath(script_path):
            return w
    return None
def move_window(match_strings=[],mon_index=0,window_info=None):
    mon_index = get_mon_index(mon_index)
    w = window_info or get_window_best_match(match_strings)
    if w:
        wid = w["window_id"]
        moved = move_window_to_monitor(wid, mon_index)
        activated = activate_window(wid)
        return {"launched": False, "window_id": wid, "moved": moved, "activated": activated}
def ensure_single_instance_or_launch(
    *,
    match_strings: List[str],
    monitor_index: int = 1,
    launch_cmd: List[str],
    cwd: Optional[str] = None,
    wait_show_sec: float = 1.0
) -> Dict[str, Union[str, bool]]:
    """
    If a window matching any of `match_titles` exists: focus and move it to the given monitor.
    Else: launch the app (once), wait briefly, then focus+move.
    Returns dict with keys: {'launched': bool, 'window_id': Optional[str]}
    """
    # 1) try to find existing
    existing = find_window_for_script(SCRIPT)
    if existing:
        return move_window(window_info=existing, mon_index=monitor_index)


    new_window_info = get_new_window_info(launch_cmd,cwd,match_strings)
    if new_window_info:
        res = move_window(window_info=new_window_info,mon_index=mon_index)
        return res   
def launch_python_conda_script(path,mon_index=0):
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    mon_index = get_mon_index(mon_index)
    CONDA_EXE = "/home/computron/miniconda/bin/conda"  # adjust if different
    ENV_NAME  = "base"
    SCRIPT    = path
    WORKDIR   = dirname
    DISPLAY   = f":{mon_index}"
    LAUNCH_CMD = [
        CONDA_EXE, "run", "-n", ENV_NAME, "--no-capture-output",
        "env", "DISPLAY=" + DISPLAY,   # ensure DISPLAY in env of child
        "python", SCRIPT
    ]
    MATCH_TITLES = [basename]
    res = ensure_single_instance_or_launch(
        match_strings=MATCH_TITLES,
        monitor_index=DISPLAY,
        launch_cmd=LAUNCH_CMD,
        cwd=WORKDIR,
        wait_show_sec=1.0,
    )
    return res
