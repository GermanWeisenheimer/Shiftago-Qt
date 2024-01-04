@echo off
setlocal

rem generate spec file
set app_name=shiftago-qt
set images_dir=shiftago/ui/images
.venv\Scripts\pyi-makespec entry_point.py --name=%app_name% --add-data "%images_dir%/*.png:%images_dir%" --add-data "%images_dir%/*.jpg:%images_dir%"

rem enhance spec file
set spec_file=%app_name%.spec
set config_file=shiftago-qt.cfg
echo import shutil>>%spec_file%
echo shutil.copyfile('%config_file%', f'{DISTPATH}/%app_name%/%config_file%')>>%spec_file%

rem run installer with enhanced spec file
.venv\Scripts\pyinstaller --clean --noconfirm %spec_file%

endlocal
