// isense5172 -- #5172 "IDxcIndex::ParseTranslationUnit has no mechanism to
// honor an IDxcIncludeHandler".
//
// The issue compares two surfaces of the SAME dxcompiler.dll:
//   IDxcCompiler::Compile()          takes an optional IDxcIncludeHandler*
//                                     (include/dxc/dxcapi.h), invoked once
//                                     per #include at parse time with the
//                                     requested filename.
//   IDxcIndex::ParseTranslationUnit  (include/dxc/dxcisense.h) takes no such
//                                     parameter at all -- only a fixed
//                                     IDxcUnsavedFile** array -- and its
//                                     implementation (dxcisenseimpl.cpp)
//                                     unconditionally binds libclang's file
//                                     access to CreateMSFileSystemForDisk(),
//                                     behind a "TODO: until an interface to
//                                     file access is defined" comment that
//                                     predates this issue.
//
// Four cases, same dxcompiler.dll, same #include:
//   pti-disk        ParseTranslationUnit, myinclude.hlsli PRESENT on disk,
//                    no unsaved files.  ANCHOR: reads disk (DISK_CONTENT_MARKER).
//   pti-absent       ... myinclude.hlsli REMOVED from disk, still no unsaved
//                    files.  The only failure mode ParseTranslationUnit has
//                    when disk does not have the answer: file-not-found.
//   pti-unsaved      ... myinclude.hlsli still removed, but pre-declared as
//                    an IDxcUnsavedFile under its exact expected relative
//                    name, matching the pattern DXC's own unit test uses
//                    (tools/clang/unittests/HLSL/DXIsenseTest.cpp,
//                    InclusionWhenValidThenAvailable, which keys "./inc.h").
//                    This is intellisense's closest substitute: a static,
//                    pre-registered table keyed by literal path, supplied
//                    before parsing starts.
//   compile-handler  IDxcCompiler::Compile, myinclude.hlsli absent from disk
//                    throughout, content supplied ONLY by a custom
//                    IDxcIncludeHandler::LoadSource callback invoked with the
//                    requested filename at resolution time. Proves Compile's
//                    surface can synthesize header content with zero disk
//                    backing and zero foreknowledge of the requested name --
//                    exactly the mechanism ParseTranslationUnit lacks.
//
// SELF-CONSISTENCY (SKILL.md, "A control cannot catch a broken reader"):
// every case's completion is checked before its result is printed; a case
// that could not run prints PROBE-INCOMPLETE and the harness exits 2 rather
// than silently omitting it. myinclude.hlsli is restored to its committed,
// on-disk content at the end regardless of how the cases above left it, so
// a rerun starts from the same state and the working tree stays clean.
//
//   set DXC_5172_DLL=<...>\dxcompiler.dll
//   isense5172.exe
//
// Run from the issue directory: repro.hlsl and myinclude.hlsli are read
// relative to the current directory.

#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "dxc/dxcapi.h"
#include "dxc/dxcisense.h"

namespace {

const char *HrName(HRESULT hr) {
  switch (hr) {
  case S_OK:
    return "S_OK";
  case E_FAIL:
    return "E_FAIL";
  case E_INVALIDARG:
    return "E_INVALIDARG";
  case E_POINTER:
    return "E_POINTER";
  case E_NOTIMPL:
    return "E_NOTIMPL";
  case E_OUTOFMEMORY:
    return "E_OUTOFMEMORY";
  case E_NOINTERFACE:
    return "E_NOINTERFACE";
  default:
    return "(other)";
  }
}

int g_incomplete = 0;

int Incomplete(const char *why) {
  printf("isense5172: PROBE-INCOMPLETE: %s\n", why);
  g_incomplete = 1;
  return 2;
}
int Incomplete(const char *why, HRESULT hr) {
  printf("isense5172: PROBE-INCOMPLETE: %s (hr=0x%08lX %s)\n", why,
         (unsigned long)hr, HrName(hr));
  g_incomplete = 1;
  return 2;
}

std::wstring Widen(const char *s) {
  int n = MultiByteToWideChar(CP_UTF8, 0, s, -1, nullptr, 0);
  std::wstring w(n ? n - 1 : 0, L'\0');
  if (n)
    MultiByteToWideChar(CP_UTF8, 0, s, -1, &w[0], n);
  return w;
}

// Collapse a diagnostic/error blob to one readable line; full text is what
// the compiler returned, only line breaks change, and the marker says so.
std::string OneLine(const char *s, size_t len) {
  std::string out;
  bool pendingBreak = false;
  for (size_t i = 0; i < len && s[i]; ++i) {
    unsigned char c = (unsigned char)s[i];
    if (c == '\r' || c == '\n') {
      pendingBreak = !out.empty();
      continue;
    }
    if (pendingBreak) {
      out += " \\n ";
      pendingBreak = false;
    }
    out += (c < 0x20 || c >= 0x7F) ? '?' : (char)c;
  }
  return out;
}

bool WriteFileText(const char *path, const char *text) {
  FILE *f = fopen(path, "wb");
  if (!f)
    return false;
  fputs(text, f);
  fclose(f);
  return true;
}

void PrintDiagnostics(IDxcTranslationUnit *tu) {
  unsigned n = 0;
  if (FAILED(tu->GetNumDiagnostics(&n))) {
    printf("  GetNumDiagnostics failed\n");
    return;
  }
  printf("  diagnostic count           %u\n", n);
  for (unsigned i = 0; i < n; ++i) {
    IDxcDiagnostic *d = nullptr;
    if (FAILED(tu->GetDiagnostic(i, &d)) || !d) {
      printf("  diagnostic[%u]              (GetDiagnostic failed)\n", i);
      continue;
    }
    LPSTR text = nullptr;
    if (SUCCEEDED(d->FormatDiagnostic(
            (DxcDiagnosticDisplayOptions)(DxcDiagnostic_DisplaySourceLocation |
                                          DxcDiagnostic_DisplayOption),
            &text)) &&
        text) {
      printf("  diagnostic[%u]              \"%s\"\n", i,
             OneLine(text, strlen(text)).c_str());
    } else {
      printf("  diagnostic[%u]              (FormatDiagnostic failed)\n", i);
    }
    d->Release();
  }
}

// Custom include handler for the compile-handler case only. It refuses
// every filename except the one under test, so a match proves THIS handler
// -- not some other fallback -- produced the content, and callCount/matched
// are the self-consistency witnesses printed alongside the result.
class HandlerLoadSource : public IDxcIncludeHandler {
public:
  std::wstring wantSuffix;
  std::string content;
  int callCount = 0;
  bool matched = false;
  IDxcLibrary *lib = nullptr;

  HRESULT STDMETHODCALLTYPE LoadSource(LPCWSTR pFilename,
                                       IDxcBlob **ppIncludeSource) override {
    callCount++;
    std::wstring name(pFilename ? pFilename : L"");
    bool isMatch = name.size() >= wantSuffix.size() &&
                   _wcsicmp(name.c_str() + (name.size() - wantSuffix.size()),
                            wantSuffix.c_str()) == 0;
    if (!isMatch) {
      *ppIncludeSource = nullptr;
      return E_FAIL; // this handler recognizes only one filename
    }
    matched = true;
    return lib->CreateBlobWithEncodingOnHeapCopy(
        content.data(), (UINT32)content.size(), CP_UTF8,
        (IDxcBlobEncoding **)ppIncludeSource);
  }
  HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void **out) override {
    if (iid == __uuidof(IUnknown) || iid == __uuidof(IDxcIncludeHandler)) {
      *out = this;
      AddRef();
      return S_OK;
    }
    *out = nullptr;
    return E_NOINTERFACE;
  }
  ULONG STDMETHODCALLTYPE AddRef() override { return ++refs; }
  ULONG STDMETHODCALLTYPE Release() override {
    ULONG r = --refs;
    if (r == 0)
      delete this;
    return r;
  }

private:
  ULONG refs = 1;
};

} // namespace

int main() {
  const char *dllEnv = getenv("DXC_5172_DLL");
  if (!dllEnv || !*dllEnv) {
    fprintf(stderr, "isense5172: set DXC_5172_DLL to a dxcompiler.dll\n");
    return 3;
  }
  printf("# isense5172: #5172 ParseTranslationUnit vs IDxcIncludeHandler\n");
  printf("dll: %s\n", dllEnv);

  if (FAILED(CoInitializeEx(nullptr, COINIT_MULTITHREADED)))
    return Incomplete("CoInitializeEx failed");

  HMODULE mod = LoadLibraryA(dllEnv);
  if (!mod)
    return Incomplete("LoadLibraryA failed on DXC_5172_DLL");
  auto createInstance =
      (DxcCreateInstanceProc)GetProcAddress(mod, "DxcCreateInstance");
  if (!createInstance)
    return Incomplete("no DxcCreateInstance export in DXC_5172_DLL");

  IDxcLibrary *lib = nullptr;
  if (FAILED(createInstance(CLSID_DxcLibrary, __uuidof(IDxcLibrary),
                            (void **)&lib)) ||
      !lib)
    return Incomplete("DxcCreateInstance(CLSID_DxcLibrary) failed");

  IDxcIntelliSense *isense = nullptr;
  if (FAILED(createInstance(CLSID_DxcIntelliSense, __uuidof(IDxcIntelliSense),
                            (void **)&isense)) ||
      !isense)
    return Incomplete("DxcCreateInstance(CLSID_DxcIntelliSense) failed");

  IDxcCompiler *compiler = nullptr;
  if (FAILED(createInstance(CLSID_DxcCompiler, __uuidof(IDxcCompiler),
                            (void **)&compiler)) ||
      !compiler)
    return Incomplete("DxcCreateInstance(CLSID_DxcCompiler) failed");

  const char *reproPath = "repro.hlsl";
  const char *incPath = "myinclude.hlsli";
  const char *diskContent = "#error DISK_CONTENT_MARKER\r\n";
  const char *handlerContent = "#error HANDLER_CONTENT_MARKER\r\n";

  bool allRan = true;

  // ---- pti-disk: myinclude.hlsli present on disk, no unsaved files -------
  if (!WriteFileText(incPath, diskContent))
    return Incomplete("could not write myinclude.hlsli (pti-disk)");
  printf(
      "\n[pti-disk] ParseTranslationUnit, myinclude.hlsli ON DISK, no unsaved files\n");
  {
    IDxcIndex *index = nullptr;
    HRESULT hrIdx = isense->CreateIndex(&index);
    if (FAILED(hrIdx) || !index) {
      allRan = false;
      printf("  skipped: CreateIndex failed (hr=0x%08lX)\n",
             (unsigned long)hrIdx);
    } else {
      IDxcTranslationUnit *tu = nullptr;
      HRESULT call = index->ParseTranslationUnit(
          reproPath, nullptr, 0, nullptr, 0, DxcTranslationUnitFlags_None,
          &tu);
      printf("  call returned              0x%08lX (%s)\n",
             (unsigned long)call, HrName(call));
      if (SUCCEEDED(call) && tu) {
        PrintDiagnostics(tu);
        tu->Release();
      } else {
        allRan = false;
        printf("  (no translation unit)\n");
      }
      index->Release();
    }
  }

  // ---- pti-absent: myinclude.hlsli removed, no unsaved files -------------
  if (!DeleteFileA(incPath))
    return Incomplete("could not delete myinclude.hlsli (pti-absent)");
  printf(
      "\n[pti-absent] ParseTranslationUnit, myinclude.hlsli REMOVED, no unsaved files\n");
  {
    IDxcIndex *index = nullptr;
    HRESULT hrIdx = isense->CreateIndex(&index);
    if (FAILED(hrIdx) || !index) {
      allRan = false;
      printf("  skipped: CreateIndex failed (hr=0x%08lX)\n",
             (unsigned long)hrIdx);
    } else {
      IDxcTranslationUnit *tu = nullptr;
      HRESULT call = index->ParseTranslationUnit(
          reproPath, nullptr, 0, nullptr, 0, DxcTranslationUnitFlags_None,
          &tu);
      printf("  call returned              0x%08lX (%s)\n",
             (unsigned long)call, HrName(call));
      if (SUCCEEDED(call) && tu) {
        PrintDiagnostics(tu);
        tu->Release();
      } else {
        allRan = false;
        printf("  (no translation unit)\n");
      }
      index->Release();
    }
  }

  // ---- pti-unsaved: myinclude.hlsli still removed, pre-declared as an ----
  // ---- IDxcUnsavedFile under its exact expected relative name ------------
  printf("\n[pti-unsaved] ParseTranslationUnit, myinclude.hlsli REMOVED, "
         "pre-declared as unsaved file \"./myinclude.hlsli\"\n");
  {
    IDxcUnsavedFile *unsaved = nullptr;
    const char *unsavedText = "#define X 1\r\n";
    HRESULT hrU = isense->CreateUnsavedFile("./myinclude.hlsli", unsavedText,
                                            (unsigned)strlen(unsavedText),
                                            &unsaved);
    if (FAILED(hrU) || !unsaved) {
      allRan = false;
      printf("  skipped: CreateUnsavedFile failed (hr=0x%08lX)\n",
             (unsigned long)hrU);
    } else {
      IDxcIndex *index = nullptr;
      HRESULT hrIdx = isense->CreateIndex(&index);
      if (FAILED(hrIdx) || !index) {
        allRan = false;
        printf("  skipped: CreateIndex failed (hr=0x%08lX)\n",
               (unsigned long)hrIdx);
      } else {
        IDxcTranslationUnit *tu = nullptr;
        HRESULT call = index->ParseTranslationUnit(
            reproPath, nullptr, 0, &unsaved, 1, DxcTranslationUnitFlags_None,
            &tu);
        printf("  call returned              0x%08lX (%s)\n",
               (unsigned long)call, HrName(call));
        if (SUCCEEDED(call) && tu) {
          PrintDiagnostics(tu);
          tu->Release();
        } else {
          allRan = false;
          printf("  (no translation unit)\n");
        }
        index->Release();
      }
      unsaved->Release();
    }
  }

  // ---- compile-handler: myinclude.hlsli still removed; content supplied -
  // ---- ONLY by a custom IDxcIncludeHandler -------------------------------
  printf("\n[compile-handler] IDxcCompiler::Compile, myinclude.hlsli "
         "REMOVED, content from a custom IDxcIncludeHandler only\n");
  {
    IDxcBlobEncoding *src = nullptr;
    HRESULT hrSrc =
        lib->CreateBlobFromFile(Widen(reproPath).c_str(), nullptr, &src);
    if (FAILED(hrSrc) || !src) {
      allRan = false;
      printf("  skipped: CreateBlobFromFile failed (hr=0x%08lX)\n",
             (unsigned long)hrSrc);
    } else {
      HandlerLoadSource *handler = new HandlerLoadSource();
      handler->wantSuffix = L"myinclude.hlsli";
      handler->content = handlerContent;
      handler->lib = lib;

      IDxcOperationResult *res = nullptr;
      HRESULT call = compiler->Compile(
          src, Widen(reproPath).c_str(), L"main", L"ps_6_0", nullptr, 0,
          nullptr, 0, handler, &res);
      printf("  call returned              0x%08lX (%s)\n",
             (unsigned long)call, HrName(call));
      printf("  handler LoadSource calls   %d\n", handler->callCount);
      printf("  handler matched request    %s\n",
             handler->matched ? "yes" : "no");
      if (SUCCEEDED(call) && res) {
        HRESULT status = E_FAIL;
        res->GetStatus(&status);
        printf("  result status              0x%08lX (%s)\n",
               (unsigned long)status, HrName(status));
        IDxcBlobEncoding *errs = nullptr;
        if (SUCCEEDED(res->GetErrorBuffer(&errs)) && errs) {
          if (errs->GetBufferSize())
            printf("  errors                     \"%s\"\n",
                   OneLine((const char *)errs->GetBufferPointer(),
                           (size_t)errs->GetBufferSize())
                       .c_str());
          errs->Release();
        }
        res->Release();
      } else {
        allRan = false;
        printf("  (no operation result)\n");
      }
      handler->Release();
      src->Release();
    }
  }

  // ---- restore myinclude.hlsli to its committed content ------------------
  if (!WriteFileText(incPath, diskContent))
    fprintf(stderr,
            "isense5172: WARNING: could not restore myinclude.hlsli\n");

  if (!allRan) {
    printf("\nisense5172: PROBE-INCOMPLETE: at least one case above did not "
           "run to completion; see \"skipped\"/\"(no ...)\" lines\n");
    return 2;
  }
  printf("\nisense5172: all four cases ran to completion\n");
  return 0;
}
