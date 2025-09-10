import subprocess
import time
from typing import List
from ..string_comp import *
from ..window_utils import *
# tweak if your browser uses Page_Down instead of Tab
NEXT_TAB_KEY = "ctrl+Tab"
# how many times to press before giving up
MAX_TABS = 50
# time for browser to update title
DELAY = 0.1
# Browser title signatures
BROWSER_PATTERNS = [
    'Mozilla', 'Firefox', 'Chrome', 'Chromium',
    'Microsoft Edge', 'Opera', 'Safari'
]
def is_browser(win):
    if get_strings_in_string(win.get('window_title'),BROWSER_PATTERNS):
        return True
    return False

def get_tab_titles(win):
    win_id = win["window_id"]
    tab_titles = cycle_tabs(win_id)
    win['tab_titles'] = tab_titles
    return win

def get_browsers(parsed_windows=None,active_windows=None):
    parsed_windows = parsed_windows or get_parsed_windows()
    browsers = [get_tab_titles(parsed_window) for parsed_window in parsed_windows if is_browser(parsed_window)]
    return browsers

def activate_window(win_id: str):
    subprocess.run(["xdotool", "windowactivate", "--sync", win_id], check=True)

def get_window_title(win_id: str) -> str:
    res = subprocess.run(
        ["xdotool", "getwindowname", win_id],
        capture_output=True, text=True, check=True
    )
    return res.stdout.strip()

def switch_tab(win_id: str):
    # sends the next‐tab key only to that window
    subprocess.run(
        ["xdotool", "key", "--window", win_id, NEXT_TAB_KEY],
        check=True
    )

def cycle_tabs(win_id: str,window_name=None) -> List[str]:
    """Returns the ordered list of tab-titles in the given window."""
    activate_window(win_id)
    first_title = get_window_title(win_id)
    titles = [first_title]

    for _ in range(MAX_TABS):
        switch_tab(win_id)
        time.sleep(DELAY)
        title = get_window_title(win_id)
        if window_name and title == window_name:
            return 
        if title == first_title:
            break
        titles.append(title)

    return titles
