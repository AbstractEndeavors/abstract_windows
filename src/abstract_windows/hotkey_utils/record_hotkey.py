#!/usr/bin/env python3
"""
Qt GUI for managing system-wide hotkeys using pynput.
Lets the user:
  • Record or type a key combo (no root required)
  • Choose or create a bash script
  • Register the hotkey globally to run the script or replay a recording
"""

from abstract_gui.QT6 import *
from threading import Thread
import subprocess, json, os, time, sys
# ---- abstract imports ---------------------------------------------------------
from abstract_utilities import safe_dump_to_file, safe_load_from_file
# ------------------------------------------------------------------------------
from abstract_clicks.managers.eventsRecorder import *

HOTKEYS_PATH = "/home/computron/.config/abstract_hotkeys.json"
CONFIG_PATH = "/home/computron/.config/abstract_hotkeys.json"
DEFAULT_SCRIPT_DIR = "/home/computron/bashScripts/hotkeys"


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
            rec = EventsRecorder(events_path=HOTKEYS_PATH)
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




class HotkeyRecorder(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Global Hotkey Manager")
        self.setGeometry(400, 300, 560, 330)

        os.makedirs(DEFAULT_SCRIPT_DIR, exist_ok=True)

        self.manager = HotkeyManager()

        # ── layout ──────────────────────────────────────────────
        self.layout = QVBoxLayout()
        self.info_label = QLabel("Press 'Record' or manually enter a hotkey combo.")
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("e.g. ctrl+alt+h")

        self.cmd_label = QLabel("Command or script to execute:")
        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.browse_btn = QPushButton("📂 Browse")
        self.new_btn = QPushButton("➕ New Script")
        cmd_row.addWidget(self.cmd_input)
        cmd_row.addWidget(self.browse_btn)
        cmd_row.addWidget(self.new_btn)

        self.record_btn = QPushButton("Record Hotkey")
        self.save_btn = QPushButton("Save / Activate")
        self.refresh_btn = QPushButton("Reload Hotkeys")
        self.stop_btn = QPushButton("Stop Listener")

        for w in [
            self.info_label, self.hotkey_input, self.cmd_label,
            self.record_btn, self.save_btn, self.refresh_btn, self.stop_btn
        ]:
            self.layout.addWidget(w)
        self.layout.insertLayout(3, cmd_row)
        self.setLayout(self.layout)

        # ── connections ─────────────────────────────────────────
        self.browse_btn.clicked.connect(self.browse_script)
        self.new_btn.clicked.connect(self.create_new_script)
        self.record_btn.clicked.connect(self.record_hotkey)
        self.save_btn.clicked.connect(self.save_hotkey)
        self.refresh_btn.clicked.connect(self.reload_hotkeys)
        self.stop_btn.clicked.connect(self.stop_hotkeys)

        # state
        self.current_combo = None
        self.listener = None

        # start listener
        self.manager.start_listener()

    # ──────────────────────────────────────────────────────────
    # file handling
    # ──────────────────────────────────────────────────────────
    def browse_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Script", DEFAULT_SCRIPT_DIR,
            "Scripts (*.sh *.py *.bash *.zsh);;All Files (*)"
        )
        if path:
            self.cmd_input.setText(path)

    def create_new_script(self):
        name, ok = QInputDialog.getText(self, "New Script", "Enter script filename (e.g. my_task.sh):")
        if not ok or not name.strip():
            return
        if not name.endswith(".sh"):
            name += ".sh"

        dest_dir = QFileDialog.getExistingDirectory(self, "Select Directory", DEFAULT_SCRIPT_DIR)
        if not dest_dir:
            dest_dir = DEFAULT_SCRIPT_DIR

        dest_path = os.path.join(dest_dir, name)
        if os.path.exists(dest_path):
            choice = QMessageBox.question(
                self, "Overwrite?",
                f"{dest_path} exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if choice == QMessageBox.No:
                return

        with open(dest_path, "w") as f:
            f.write("#!/bin/bash\n\n# Hotkey script\n\n")
        os.chmod(dest_path, 0o755)
        self.cmd_input.setText(dest_path)

        editor = os.environ.get("EDITOR") or next(
            (e for e in ["code", "gedit", "nano", "xdg-open"]
             if subprocess.call(f"which {e}", shell=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL) == 0),
            None)
        if editor:
            subprocess.Popen([editor, dest_path])
        QMessageBox.information(self, "Script Created", f"New script created at:\n{dest_path}")

    # ──────────────────────────────────────────────────────────
    # hotkey recording (within GUI focus)
    # ──────────────────────────────────────────────────────────
    def record_hotkey(self):
        self.info_label.setText("Press your desired combo now…")
        self.current_combo = []

        def on_press(key):
            try:
                k = key.char.lower()
            except AttributeError:
                k = str(key).replace("Key.", "").lower()
            if k not in self.current_combo:
                self.current_combo.append(k)

        def on_release(key):
            if len(self.current_combo) > 1:
                combo = '+'.join(self.current_combo)
                self.hotkey_input.setText(combo)
                self.info_label.setText(f"Recorded: {combo}")
                return False  # stop listener
            return True

        Thread(target=lambda: keyboard.Listener(on_press=on_press,
                                                on_release=on_release).run()).start()

    # ──────────────────────────────────────────────────────────
    # hotkey storage
    # ──────────────────────────────────────────────────────────
    def save_hotkey(self):
        combo = self.hotkey_input.text().strip().lower()
        command = self.cmd_input.text().strip()
        if not combo or not command:
            QMessageBox.warning(self, "Missing Data",
                                "Please enter a hotkey and command/script path.")
            return

        existing = self.manager.hotkeys.get(combo)
        if existing and existing != command:
            choice = QMessageBox.question(
                self, "Replace Hotkey",
                f"'{combo}' already runs:\n{existing}\nReplace it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if choice == QMessageBox.No:
                return

        self.manager.add_hotkey(combo, command)
        self.manager.start_listener()
        QMessageBox.information(self, "Saved",
                                f"Hotkey '{combo}' → {command} activated.")

    def reload_hotkeys(self):
        self.manager.hotkeys = self.manager.load_hotkeys()
        self.manager.start_listener()
        QMessageBox.information(self, "Reloaded", "All saved hotkeys re-registered.")

    def stop_hotkeys(self):
        self.manager.stop_listener()
        QMessageBox.information(self, "Stopped", "Global hotkey listener stopped.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HotkeyRecorder()
    window.show()
    sys.exit(app.exec())
