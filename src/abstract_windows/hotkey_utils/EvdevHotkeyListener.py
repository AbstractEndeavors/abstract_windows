# File: hotkey_listener.py
import threading
import os
from evdev import InputDevice, ecodes, categorize
import functools

class EvdevHotkeyListener:
    def __init__(self, device_path, combo_keys, callback):
        """
        device_path: str e.g. "/dev/input/event3"
        combo_keys: set of keycode names e.g. {"KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_H"}
        callback: function to call when combo pressed
        """
        self.device_path = device_path
        self.combo_keys = combo_keys
        self.callback = callback
        self._running = False
        self._thread = None
        self._pressed = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None

    def _listen_loop(self):
        dev = InputDevice(self.device_path)
        for event in dev.read_loop():
            if not self._running:
                break
            if event.type == ecodes.EV_KEY:
                key = ecodes.KEY[event.code] if event.code in ecodes.KEY else None
                if key:
                    if event.value == 1:  # key down
                        self._pressed.add(key)
                    elif event.value == 0:  # key up
                        self._pressed.discard(key)
                    # Check if combo matched
                    if self.combo_keys.issubset(self._pressed):
                        # trigger callback
                        try:
                            self.callback()
                        except Exception as e:
                            print("Hotkey callback error:", e)
                        # optional: clear pressed so it isn't retriggered immediately
                        self._pressed.clear()
