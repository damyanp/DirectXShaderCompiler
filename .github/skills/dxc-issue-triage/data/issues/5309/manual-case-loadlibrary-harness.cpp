// manual-case-loadlibrary-harness.cpp (#5309)
//
// Isolates the exact mechanism dxbc2dxil.cpp's Converter::GetDxcCreateInstance
// uses to obtain the DxbcConverter factory: LoadLibraryExW with
// LOAD_LIBRARY_SEARCH_APPLICATION_DIR, followed by HRESULT_FROM_WIN32(GetLastError())
// on failure. This does not build or link any part of DXC; it is a standalone
// reproduction of the Win32/HRESULT arithmetic against a real (guaranteed-absent)
// module name, to confirm what error code that specific failure path reports.
#include <windows.h>
#include <cstdio>

int main() {
  // (1) A module name guaranteed not to exist next to this harness or
  //     anywhere on the search path, exercising exactly the branch
  //     dxbc2dxil.cpp takes when "dxilconv.dll" (or one of its DLL
  //     dependencies) is missing from the application directory.
  const wchar_t *missingModule = L"dxilconv-5309-does-not-exist.dll";
  SetLastError(0);
  HMODULE hModule = LoadLibraryExW(missingModule, NULL,
                                    LOAD_LIBRARY_SEARCH_APPLICATION_DIR);
  DWORD gle = GetLastError();
  HRESULT hr = (hModule == NULL) ? HRESULT_FROM_WIN32(gle) : S_OK;
  printf("LoadLibraryExW(\"missing\", LOAD_LIBRARY_SEARCH_APPLICATION_DIR):\n");
  printf("  hModule = %p\n", (void *)hModule);
  printf("  GetLastError() = %lu (0x%08lX)\n", gle, gle);
  printf("  HRESULT_FROM_WIN32(GetLastError()) = 0x%08X\n", hr);
  printf("  matches issue's reported 0x8007007e: %s\n",
         (hr == (HRESULT)0x8007007eu) ? "YES" : "no");
  printf("\n");

  // (2) Control: kernel32.dll always exists and always loads, proving the
  //     harness's success path is distinguishable from its failure path
  //     (this is not a broken loader/link environment reporting failure for
  //     everything).
  SetLastError(0);
  HMODULE hControl = LoadLibraryExW(L"kernel32.dll", NULL,
                                     LOAD_LIBRARY_SEARCH_SYSTEM32);
  printf("Control: LoadLibraryExW(\"kernel32.dll\", SEARCH_SYSTEM32):\n");
  printf("  hModule = %p (%s)\n", (void *)hControl,
         hControl != NULL ? "loaded OK" : "FAILED -- unexpected");
  printf("\n");

  // (3) Second control: ERROR_FILE_NOT_FOUND (2), the code an absent *input*
  //     file (as opposed to an absent DLL) would produce via
  //     hlsl::ReadBinaryFile's own IFT(...) path, to show the two failure
  //     modes are numerically distinct and neither could be mistaken for the
  //     other from the printed HRESULT alone.
  HRESULT hrFileNotFound = HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND);
  printf("Control: HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND=2) = 0x%08X "
         "(distinct from module-not-found)\n",
         hrFileNotFound);

  return 0;
}
