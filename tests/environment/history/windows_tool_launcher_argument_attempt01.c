/* Windows command-name adapters for the unchanged Python security gate.
 * Forward every argument and the real exit code; never change gate behavior.
 * gcc -municode -O2 windows_tool_launcher.c -o npm.exe; copy as python3.exe.
 */
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

int wmain(int argc, wchar_t **argv) {
    wchar_t *name = wcsrchr(argv[0], L'\\');
    name = name ? name + 1 : argv[0];
    int python = !_wcsicmp(name, L"python3.exe") || !_wcsicmp(name, L"python3");
    wchar_t *exe = _wgetenv(python ? L"QA_TOOL_PYTHON" : L"QA_TOOL_NODE");
    wchar_t *cli = _wgetenv(L"QA_TOOL_NPM_CLI");
    if (!exe || (!python && !cli)) {
        fputs("Explicit QA tool paths are required\n", stderr);
        return 127;
    }
    wchar_t **args = calloc((size_t)argc + 3, sizeof(wchar_t *));
    if (!args) return 127;
    int n = 0;
    args[n++] = exe;
    if (python) { args[n++] = L"-X"; args[n++] = L"utf8"; }
    else args[n++] = cli;
    for (int i = 1; i < argc; i++) args[n++] = argv[i];
    intptr_t code = _wspawnv(_P_WAIT, exe, (const wchar_t *const *)args);
    free(args);
    if (code < 0) { fputs("QA tool launch failed\n", stderr); return 127; }
    return (int)code;
}
