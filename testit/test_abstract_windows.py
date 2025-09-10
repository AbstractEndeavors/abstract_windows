import os
from abstract_windows import *

MATCH_TITLES = ["finditGUI.py"]


get_monitors()               
CONDA_EXE = "/home/computron/miniconda/bin/conda"  # adjust if different
ENV_NAME  = "base"
SCRIPT    = "/home/computron/Documents/pythonTools/modules/abstract_ide/finditGUI.py"
WORKDIR   = os.path.dirname(SCRIPT)
DISPLAY   = ":0"



LAUNCH_CMD = [
    CONDA_EXE, "run", "-n", ENV_NAME, "--no-capture-output",
    "env", "DISPLAY=" + DISPLAY,   # ensure DISPLAY in env of child
    "python", SCRIPT
]

res = ensure_single_instance_or_launch(
    match_strings=MATCH_TITLES,
    monitor_index=DISPLAY,
    launch_cmd=LAUNCH_CMD,
    cwd=WORKDIR,
    wait_show_sec=1.0,
)
print(res)
