from pathlib import Path
import shutil

def post_build(interface) -> None:
    """
    Pyinstaller post build hook. Copies config file to the dist folder.
    """
    dist_path = Path("dist", "pyinstaller", interface.platform)
    shutil.copy('shiftago-qt.cfg', dist_path)
