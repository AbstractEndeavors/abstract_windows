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
def get_new_window_info(launch_cmd,cwd,match_strings):
    window_ids = get_all_window_ids()
    proc = subprocess.Popen(launch_cmd, cwd=cwd)
    while True:
        win_list = filter_win_list(window_ids)
        window_best_match = get_window_best_match(windows_list=win_list,match_strings=match_strings)
        if window_best_match:
            return window_best_match
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
    mon_index = get_mon_index(monitor_index)
    window_best_match = get_window_best_match(match_strings=match_strings)
    if window_best_match:
        res = move_window(window_info = window_best_match,mon_index=mon_index)
        return res

    new_window_info = get_new_window_info(launch_cmd,cwd,match_strings)
    if new_window_info:
        res = move_window(window_info=new_window_info,mon_index=mon_index)
        return res   
