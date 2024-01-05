@echo off
setlocal

set scripts_dir=.venv\Scripts

rem generate spec file
set app_name=shiftago-qt
set images_dir=shiftago/ui/images
%scripts_dir%\pyi-makespec entry_point.py --name=%app_name% --noconsole^
    --add-data "%images_dir%/*.png:%images_dir%"^
    --add-data "%images_dir%/*.jpg:%images_dir%"

rem enhance spec file
set spec_file=%app_name%.spec
echo import shutil>>%spec_file%
echo shutil.copy('shiftago-qt.cfg', f'{DISTPATH}/{specnm}')>>%spec_file%

rem run installer with enhanced spec file
%scripts_dir%\pyinstaller %spec_file% --clean --noconfirm

endlocal
