// Control A for #5079: DXC's own headers alone, non-Windows, no
// DirectX-Headers shim in the translation unit. Must compile clean --
// proves dxc/WinAdapter.h is not broken by itself, only in combination with
// a second, independent shim providing the same names (see repro.cpp).

#include <dxc/dxcapi.h>

int main() { return 0; }
