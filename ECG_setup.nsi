; ECG_Installer.nsi
Unicode true
Name "ECG"
OutFile "ECG_Setup.exe"
InstallDir "$PROGRAMFILES\ECG"
RequestExecutionLevel admin

!include LogicLib.nsh

Section "Main Section"
    
    SetOutPath $INSTDIR
    
    
    File /r "C:\Users\user\Documents\GitHub\EKG\*"
    
    
    nsExec::ExecToStack 'python --version'
    Pop $0
    Pop $1
    ${If} $0 != 0
        MessageBox MB_ICONSTOP|MB_OK "Python not found! Install Python 3.9+ and add to PATH."
        Abort
    ${EndIf}
    
    
    nsExec::ExecToStack 'pip install pyinstaller'
    nsExec::ExecToStack 'pip install -r "$INSTDIR\requirements.txt"'
    
    
    nsExec::ExecToStack 'pyinstaller --noconfirm --onefile --windowed --icon "$INSTDIR\icon.ico" --name "ECG" --add-data "$INSTDIR\ekg.py;." --hidden-import scipy --add-data "$INSTDIR\ui_file.py;." "$INSTDIR\main.py" --distpath "$INSTDIR" --workpath "$INSTDIR\build" --specpath "$INSTDIR\build"'
    
    
    IfFileExists "$INSTDIR\ECG.exe" 0 +3
        MessageBox MB_OK "Complete!"
    Goto +2
        MessageBox MB_ICONSTOP|MB_OK "Error! EXE-file not compile."
    
    
    CreateShortCut "$DESKTOP\ECG.lnk" "$INSTDIR\ECG.exe" "" "$INSTDIR\icon.ico"
SectionEnd

Section "Uninstall"
    
    RMDir /r "$INSTDIR"
    
    
    Delete "$DESKTOP\ECG.lnk"
    
    
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ECG"
SectionEnd