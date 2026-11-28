; Project-Friday-Setup.exe: Windows installer of the release package (built by packaging/make_windows_zip.py with makensis,
; e.g. `apt-get install nsis` in GitHub Actions). It contains exactly the files of the zip package: NO ROM, nothing generated.
;   makensis -DSRC=<package folder> -DOUTFILE=<Setup.exe> -DVERSION=<v1.2.3> installer_win.nsi
; User wishes 2026-11-19: one exe instead of a zip; the player picks the folder (default: per user, no admin); Program Files etc.
; work too (the installer restarts itself with admin rights); the uninstaller removes only the program, the built game and the
; settings only on request (checkbox, off by default); save files lie next to the player's ROM and are never touched.
Unicode true
SetCompressor /SOLID lzma
!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef VERSION
  !define VERSION "dev"
!endif
!define REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Project-Friday"
Var BuildDir   ; GitHub #26: the build folder the player chose (firstrun.py writes $INSTDIR\build_folder.txt, UTF-16LE with BOM)

Name "Project-Friday ${VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\Project-Friday"
InstallDirRegKey HKCU "Software\Project-Friday" "InstallDir"
RequestExecutionLevel user
ManifestDPIAware true
BrandingText "Project-Friday ${VERSION}"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\Project-Friday.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

!insertmacro MUI_PAGE_WELCOME
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE DirLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "German"

LangString AdminAsk ${LANG_ENGLISH} "Windows only allows administrators to write to this folder:$\r$\n$INSTDIR$\r$\n$\r$\nRestart the installer with administrator rights? (No = pick another folder)"
LangString AdminAsk ${LANG_GERMAN} "In diesen Ordner dürfen unter Windows nur Administratoren schreiben:$\r$\n$INSTDIR$\r$\n$\r$\nInstaller mit Administratorrechten neu starten? (Nein = anderen Ordner wählen)"
LangString NotEmpty ${LANG_ENGLISH} "This folder is not empty and holds no Project-Friday installation:$\r$\n$INSTDIR$\r$\n$\r$\nPlease pick an empty or new folder (e.g. ...\Project-Friday)."
LangString NotEmpty ${LANG_GERMAN} "Dieser Ordner ist nicht leer und enthält keine Project-Friday-Installation:$\r$\n$INSTDIR$\r$\n$\r$\nBitte einen leeren oder neuen Ordner wählen (z. B. ...\Project-Friday)."
LangString NoWrite ${LANG_ENGLISH} "Cannot write to this folder:$\r$\n$INSTDIR$\r$\n$\r$\nPlease pick another folder."
LangString NoWrite ${LANG_GERMAN} "In diesen Ordner kann nicht geschrieben werden:$\r$\n$INSTDIR$\r$\n$\r$\nBitte einen anderen Ordner wählen."
LangString SecUnProg ${LANG_ENGLISH} "Program files, shortcuts"
LangString SecUnProg ${LANG_GERMAN} "Programmdateien, Verknüpfungen"
LangString SecMain ${LANG_ENGLISH} "Project-Friday (required)"
LangString SecMain ${LANG_GERMAN} "Project-Friday (benötigt)"
LangString SecDesk ${LANG_ENGLISH} "Desktop shortcut"
LangString SecDesk ${LANG_GERMAN} "Verknüpfung auf dem Desktop"
LangString SecUnData ${LANG_ENGLISH} "Also delete the built game (also in a build folder you chose) and the settings (save files next to your ROM are kept)"
LangString SecUnData ${LANG_GERMAN} "Auch das gebaute Spiel (auch in einem selbst gewählten Build-Ordner) und die Einstellungen löschen (Spielstände neben deiner ROM bleiben)"

Function .onInit
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

; the chosen folder must be writable (else: restart elevated) and must not be a foreign, non-empty folder (the uninstaller removes the folder)
Function DirLeave
  IfFileExists "$INSTDIR\Project-Friday.exe" writable_check 0
  ${DirState} "$INSTDIR" $0
  StrCmp $0 "1" 0 writable_check
  MessageBox MB_ICONEXCLAMATION|MB_OK "$(NotEmpty)"
  Abort
writable_check:
  ClearErrors
  CreateDirectory "$INSTDIR"
  FileOpen $1 "$INSTDIR\pf_write_test.tmp" w
  IfErrors 0 writable
  UserInfo::GetAccountType
  Pop $2
  StrCmp $2 "Admin" 0 ask        ; already elevated and still not writable: no restart loop
  MessageBox MB_ICONEXCLAMATION|MB_OK "$(NoWrite)"
  Abort
ask:
  MessageBox MB_ICONQUESTION|MB_YESNO "$(AdminAsk)" IDYES elevate
  Abort
elevate:
  ExecShell "runas" "$EXEPATH" "/D=$INSTDIR"
  Quit
writable:
  FileClose $1
  Delete "$INSTDIR\pf_write_test.tmp"
FunctionEnd

Section "$(SecMain)" SecMainId
  SectionIn RO
  SetOutPath "$INSTDIR"
  ; an update replaces the program files completely (old tools / data must not stay behind)
  RMDir /r "$INSTDIR\tools"
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\lang"
  RMDir /r "$INSTDIR\vendor"
  RMDir /r "$INSTDIR\python"
  File /r "${SRC}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Project-Friday"
  CreateShortcut "$SMPROGRAMS\Project-Friday\Project-Friday.lnk" "$INSTDIR\Project-Friday.exe"
  CreateShortcut "$SMPROGRAMS\Project-Friday\Uninstall Project-Friday.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Project-Friday\Change build folder.lnk" "$INSTDIR\Project-Friday.exe" "--choose-build-folder"   ; GitHub #26
  WriteRegStr HKCU "Software\Project-Friday" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "DisplayName" "Project-Friday"
  WriteRegStr HKCU "${REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${REGKEY}" "Publisher" "Project-Friday (cmdrlucid)"
  WriteRegStr HKCU "${REGKEY}" "URLInfoAbout" "https://github.com/cmdrlucid/Project-Friday"
  WriteRegStr HKCU "${REGKEY}" "DisplayIcon" "$INSTDIR\Project-Friday.exe"
  WriteRegStr HKCU "${REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${REGKEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "${REGKEY}" "EstimatedSize" $0
SectionEnd

Section "$(SecDesk)" SecDeskId
  CreateShortcut "$DESKTOP\Project-Friday.lnk" "$INSTDIR\Project-Friday.exe"
SectionEnd

; ---------------------------------------------------------------- uninstaller
Function un.onInit
  !insertmacro MUI_UNGETLANGUAGE
  ; GitHub #26: remember the chosen build folder before the program files (with build_folder.txt) are removed
  StrCpy $BuildDir ""
  ClearErrors
  FileOpen $3 "$INSTDIR\build_folder.txt" r
  IfErrors bf_done
  FileSeek $3 2          ; skip the BOM
  FileReadUTF16LE $3 $BuildDir
  FileClose $3
bf_trim:
  StrCpy $4 $BuildDir 1 -1
  StrCmp $4 "$\r" bf_cut
  StrCmp $4 "$\n" bf_cut
  Goto bf_done
bf_cut:
  StrCpy $BuildDir $BuildDir -1
  Goto bf_trim
bf_done:
  ; installed into a protected folder (Program Files): restart the uninstaller with admin rights (once)
  ClearErrors
  FileOpen $1 "$INSTDIR\pf_write_test.tmp" w
  IfErrors 0 un_ok
  UserInfo::GetAccountType
  Pop $2
  StrCmp $2 "Admin" un_done
  ExecShell "runas" '"$INSTDIR\Uninstall.exe"'
  Quit
un_ok:
  FileClose $1
  Delete "$INSTDIR\pf_write_test.tmp"
un_done:
FunctionEnd

Section "un.$(SecUnProg)" SecUnProgId
  SectionIn RO
  ; only what the installer put there (never RMDir /r $INSTDIR: the player may have chosen a folder with own files next to it)
  RMDir /r "$INSTDIR\tools"
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\lang"
  RMDir /r "$INSTDIR\vendor"
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\licenses"
  RMDir /r "$INSTDIR\docs"
  RMDir /r "$INSTDIR\src"
  RMDir /r "$INSTDIR\__pycache__"
  Delete "$INSTDIR\Project-Friday.exe"
  Delete "$INSTDIR\firstrun.py"
  Delete "$INSTDIR\build.sh"
  Delete "$INSTDIR\recomp.json"
  Delete "$INSTDIR\README.txt"
  Delete "$INSTDIR\build_folder.txt"
  Delete "$INSTDIR\Change build folder.bat"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\Project-Friday\Project-Friday.lnk"
  Delete "$SMPROGRAMS\Project-Friday\Uninstall Project-Friday.lnk"
  Delete "$SMPROGRAMS\Project-Friday\Change build folder.lnk"
  RMDir "$SMPROGRAMS\Project-Friday"
  Delete "$DESKTOP\Project-Friday.lnk"
  DeleteRegKey HKCU "${REGKEY}"
  DeleteRegKey HKCU "Software\Project-Friday"
SectionEnd

Section /o "un.$(SecUnData)" SecUnDataId
  ; built game + remembered ROM path (firstrun.py DATA) and the game's settings files (%USERPROFILE%\.landstalker_*)
  RMDir /r "$LOCALAPPDATA\Project-Friday"
  ; GitHub #26: a build folder the player chose elsewhere; only our own sub folder (its name is checked: never a folder of the player's)
  StrCmp $BuildDir "" bd_skip
  StrCpy $4 $BuildDir "" -20
  StrCmp $4 "Project-Friday-Build" 0 bd_skip
  RMDir /r "$BuildDir"
bd_skip:
  Delete "$PROFILE\.landstalker_*"
SectionEnd
