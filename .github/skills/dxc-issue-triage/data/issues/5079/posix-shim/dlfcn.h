// Minimal declaration-only stand-in for glibc's <dlfcn.h>, used only because
// this repro is compiled on a Windows host with no Linux sysroot available.
//
// This is NOT part of the conflict under test (see expected.md / notes.md):
// dxc/dxcapi.h unconditionally `#include <dlfcn.h>` on the non-Windows
// branch, and there is no such header at all in the Windows SDK/MSVC
// include path, so `-fsyntax-only` cannot get past that line without one.
// It exists purely to let parsing reach the code that IS under test (the
// WinAdapter.h vs. DirectX-Headers typedef redefinition) -- it declares
// symbols, never calls or links them, and `-fsyntax-only` performs no
// linking, so a real implementation is not needed to reach or evaluate the
// conflict.
#pragma once

extern "C" {

#define RTLD_LAZY 1
#define RTLD_NOW 2

void *dlopen(const char *filename, int flags);
int dlclose(void *handle);
void *dlsym(void *handle, const char *symbol);
char *dlerror(void);

} // extern "C"
