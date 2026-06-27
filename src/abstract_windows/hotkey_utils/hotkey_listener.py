from pynput import keyboard
from threading import Thread
from abstract_utilities import safe_load_from_file, safe_dump_to_file
from abstract_clicks import EventsRecorder

import os, time, subprocess

HOTKEYS_PATH = "/home/computron/.config/abstract_hotkeys.json"


class HotkeyManager:
    def __init__(self):
        self.hotkeys = self.load_hotkeys()
        self.listener = None

    def load_hotkeys(self):
        if os.path.exists(HOTKEYS_PATH):
            return safe_load_from_file(HOTKEYS_PATH)
        return {}

    def save_hotkeys(self):
        safe_dump_to_file(self.hotkeys, HOTKEYS_PATH)

    def add_hotkey(self, combo, action):
        """Register a hotkey combo → action command or event replay."""
        combo = combo.lower()
        self.hotkeys[combo] = action
        self.save_hotkeys()
        print(f"✅ Hotkey added: {combo} → {action}")

    def remove_hotkey(self, combo):
        if combo.lower() in self.hotkeys:
            del self.hotkeys[combo]
            self.save_hotkeys()
            print(f"🗑️ Hotkey removed: {combo}")

    def _make_combination(self, combo_str):
        """Convert 'ctrl+alt+m' into a set of Key/char objects."""
        parts = combo_str.lower().split('+')
        mapping = {
            'ctrl': keyboard.Key.ctrl_l,
            'alt': keyboard.Key.alt_l,
            'shift': keyboard.Key.shift,
            'cmd': keyboard.Key.cmd,
            'win': keyboard.Key.cmd
        }
        combo = set()
        for p in parts:
            combo.add(mapping.get(p, p))
        return combo

    def _run_action(self, action):
        """Dispatch either a command or replay event."""
        if action.startswith("replay:"):
            evt = action.split(":", 1)[1]
            print(f"▶ Replaying events: {evt}")
            rec = EventsRecorder()
            Thread(target=lambda: rec.replay(evt)).start()
        else:
            print(f"▶ Running shell: {action}")
            subprocess.Popen(action, shell=True)

    def _build_hotkey_map(self):
        hotkey_map = {}
        for combo_str, action in self.hotkeys.items():
            combo = tuple(combo_str.split('+'))
            hotkey_map[combo] = lambda act=action: self._run_action(act)
        return hotkey_map

    def start_listener(self):
        if self.listener:
            self.listener.stop()
        hotkey_map = self._build_hotkey_map()
        self.listener = keyboard.GlobalHotKeys(hotkey_map)
        self.listener.start()
        print("🎧 Global hotkey listener running...")

    def stop_listener(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
            print("⏹️ Hotkey listener stopped.")
