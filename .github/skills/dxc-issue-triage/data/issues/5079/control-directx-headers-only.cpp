// Control B for #5079: DirectX-Headers' own non-Windows shim alone, no DXC
// headers in the translation unit. Must compile clean -- proves the shim is
// not broken by itself either; the conflict in repro.cpp is specifically
// the coexistence of the two shims.
//
// Deliberately does not also include <directx/d3d12shader.h>: that header
// additionally needs COM plumbing (a bare `THIS` macro) that neither this
// shim nor DXC's WinAdapter.h happens to define, which is an unrelated
// completeness gap, not part of the typedef conflict under test. Exercise
// the same conflicting names control-dxc-only.cpp exercises from the DXC
// side, so the two controls are a matched pair.

#include <wsl/winadapter.h>

BYTE b;
BOOLEAN bn;
BOOL bl;
LONG l;
ULONG ul;
LONGLONG ll;
LONG_PTR lp;
ULONG_PTR ulp;
ULONGLONG ull;
GUID g;
REFGUID rg = g;

int main() { return 0; }
