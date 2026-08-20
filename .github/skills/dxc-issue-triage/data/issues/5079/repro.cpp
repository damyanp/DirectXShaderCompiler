// #5079 repro: DXC's own non-Windows shim (dxc/WinAdapter.h, pulled in by
// dxc/dxcapi.h) redefines Windows base types that DirectX-Headers' own
// non-Windows shim already defines.
//
// Minimal by design, and deliberately does not also include
// <directx/d3d12shader.h> or <unknwn.h>, matching the reporter's own
// include list: those pull in COM interface declarations that need a bare
// `THIS` macro neither shim defines (an unrelated completeness gap -- see
// manual-case-clang-control-directx-headers-only.txt, which fails on
// exactly that when d3d12shader.h is added, with no typedef conflict in
// sight). The reporter's own error transcript never mentions d3d12shader.h
// class declarations either -- every reported error is one of the typedef
// redefinitions reproduced here.
//
// Compiled with `_WIN32` undefined (see gen-manual-case.py), matching a
// genuine non-Windows target -- both shims are gated on `#ifndef _WIN32`.

#include <wsl/winadapter.h>     // DirectX-Headers' own non-Windows shim
#include <dxc/dxcapi.h>         // pulls in DXC's own dxc/WinAdapter.h

int main() { return 0; }

