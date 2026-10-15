/* Project-Friday.exe: tiny launcher of the Windows package. Starts the bundled Python with firstrun.py and passes all arguments on.
   (console program: the progress of the first start is shown as text in its window) */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

int wmain(int argc, wchar_t **argv) {
    wchar_t dir[MAX_PATH], py[MAX_PATH + 32], pyhome[MAX_PATH + 16], script[MAX_PATH + 32];
    wchar_t *cmd, *p, *rest;
    STARTUPINFOW si; PROCESS_INFORMATION pi; DWORD code = 1; size_t n;
    (void)argc; (void)argv;
    if (!GetModuleFileNameW(NULL, dir, MAX_PATH)) { fprintf(stderr, "cannot find my own folder\n"); return 1; }
    p = wcsrchr(dir, L'\\'); if (p) *p = 0;
    swprintf(pyhome, MAX_PATH + 16, L"%ls\\python", dir);
    swprintf(py, MAX_PATH + 32, L"%ls\\python\\python.exe", dir);
    swprintf(script, MAX_PATH + 32, L"%ls\\firstrun.py", dir);
    if (GetFileAttributesW(py) == INVALID_FILE_ATTRIBUTES) { fprintf(stderr, "python\\python.exe is missing: extract the whole zip file and start Project-Friday.exe from the extracted folder.\n"); getchar(); return 1; }
    SetEnvironmentVariableW(L"PYTHONHOME", pyhome);
    SetEnvironmentVariableW(L"PYTHONPATH", NULL);
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"PYTHONNOUSERSITE", L"1");
    /* the arguments after the program name, as typed */
    rest = GetCommandLineW();
    if (*rest == L'"') { rest++; while (*rest && *rest != L'"') rest++; if (*rest) rest++; }
    else { while (*rest && *rest != L' ' && *rest != L'\t') rest++; }
    n = wcslen(py) + wcslen(script) + wcslen(rest) + 16;
    cmd = (wchar_t *)malloc(n * sizeof(wchar_t));
    swprintf(cmd, n, L"\"%ls\" \"%ls\"%ls", py, script, rest);
    memset(&si, 0, sizeof si); si.cb = sizeof si;
    if (!CreateProcessW(NULL, cmd, NULL, NULL, TRUE, 0, NULL, dir, &si, &pi)) {
        fprintf(stderr, "cannot start the bundled Python (error %lu)\n", GetLastError()); getchar(); return 1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    if (code != 0 && code != 2) { fprintf(stderr, "\nProject-Friday stopped (code %lu). Press Enter to close this window.\n", code); getchar(); }
    return (int)code;
}
