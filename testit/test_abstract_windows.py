
import shlex, os
from abstract_windows import ensure_single_instance_or_launch
match_titles = os.environ["MATCH_TITLES"].split("||")
cmd = os.environ["LAUNCH_CMD"].split("\x1f")  # unit separator for robust splitting
res = ensure_single_instance_or_launch(
    match_titles=match_titles,
    monitor_index=1,
    launch_cmd=cmd,
    cwd=os.environ["WORKDIR"] or None,
    wait_show_sec=1.0,
)
print(res)
