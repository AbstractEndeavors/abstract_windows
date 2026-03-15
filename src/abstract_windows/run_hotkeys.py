from abstract_utilities import *
from abstract_clicks.managers.eventsRecorder import *
HOTKEYS_PATH = "~/.config/abstract_hotkeys.json"

##event_mgr = record_session(HOTKEYS_PATH)
datas = safe_load_from_json(HOTKEYS_PATH)
for key,values in datas.items():
    for value in values:
        if value.get('type') in ['key_release','key_press']:
           input(value) 
