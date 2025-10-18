from src.abstract_windows.window_utils.instance_utils import edit_python_conda_script,launch_python_conda_script

result = edit_python_conda_script(
    path="/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py"
)
launch_python_conda_script(
    path="/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py"
)
print(result)
