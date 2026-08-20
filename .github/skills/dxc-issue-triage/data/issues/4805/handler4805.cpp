// handler4805 -- #4805 "Compiler does not use the custom include handler
// when compiling with `-Zi`"
//
// The reported defect is specific to the IDxcCompiler/IDxcCompiler3 API: a
// caller supplies a custom IDxcIncludeHandler so it can serve #include'd
// files from somewhere other than a plain relative-to-cwd disk path (the
// reporter's example resolves relative to the including file, like C++).
// `dxc.exe` cannot exercise this at all -- its command-line driver always
// builds its own disk-backed include handler, so the substitution point the
// bug lives in is never reached (SKILL.md, "register the harness as a
// compiler" -- the PIX-passes and reflection precedent, #2918/#4619/#4256).
//
// This harness implements the simplest possible custom IDxcIncludeHandler:
// it serves ONE #include candidate purely from an in-process string literal
// (never touching disk for that file at all) and fails LoadSource for any
// other candidate. That is strictly stronger evidence than a CWD-dependent
// disk repro: it proves the compiler either does or does not use the
// content the handler supplied, independent of any coincidental raw-path
// match on disk.
//
// The known content of the served include carries a unique marker
// (kIncludeMarker). If the compiler's SPIR-V debug-info source embedding
// (EmitVisitor.cpp's ReadSourceCode, invoked from getChoppedSourceCode /
// generateChoppedSource) actually used the handler's buffer, that marker
// would appear verbatim in the emitted container's OpString/DebugSource
// text -- SPIR-V string literals are packed as contiguous ASCII words, so a
// plain byte search over the raw container is sufficient; no disassembler
// is required. Every LoadSource call is logged, which is the harness's
// self-consistency check (SKILL.md, "a control cannot catch a broken
// reader"): if the marker is absent, the transcript still shows whether the
// handler was even asked for the file, distinguishing "handler ignored"
// from "wrong candidate spelling".
//
//   set DXC_INCLUDE_DLL=<...>\dxcompiler.dll
//   handler4805.exe -T cs_6_0 -E main -spirv -fspv-debug=vulkan-with-source
//                    -Fo out.spv repro.hlsl
//
// Registered as a compiler (SKILL.md) so `triage.py run`, `--expect` and
// `reindex` keep applying to it; DXC_INCLUDE_DLL lets the same binary be
// pointed at any release's dxcompiler.dll for a release-history matrix,
// exactly like refl4619/refl2952/run-fc2604.

#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "dxc/dxcapi.h"

namespace {

// The literal text of the "included" file. It exists ONLY here -- there is
// no file on disk anywhere named "Includes/Uniforms.hlsl" (or any spelling
// of it) for this harness to accidentally read instead.
const char *kIncludeMarker = "HANDLER4805_MARKER_f3c9a1";
std::string IncludedFileContent() {
  std::string s = "// ";
  s += kIncludeMarker;
  s += "\nRWStructuredBuffer<float> g_Buffer : register(u0);\n"
       "cbuffer Uniforms : register(b0) { float g_Value; };\n";
  return s;
}

typedef HRESULT(__stdcall *DxcCreateInstanceProc)(REFCLSID, REFIID, LPVOID *);

std::wstring Widen(const std::string &s) {
  int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
  std::wstring w(n ? n - 1 : 0, L'\0');
  if (n)
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &w[0], n);
  return w;
}

std::string Narrow(LPCWSTR s) {
  if (!s)
    return std::string();
  int n = WideCharToMultiByte(CP_UTF8, 0, s, -1, nullptr, 0, nullptr, nullptr);
  std::string r(n ? n - 1 : 0, '\0');
  if (n)
    WideCharToMultiByte(CP_UTF8, 0, s, -1, &r[0], n, nullptr, nullptr);
  return r;
}

const char *HrName(HRESULT hr) {
  switch (hr) {
  case S_OK:
    return "S_OK";
  case E_FAIL:
    return "E_FAIL";
  case E_INVALIDARG:
    return "E_INVALIDARG";
  case E_NOTIMPL:
    return "E_NOTIMPL";
  case E_NOINTERFACE:
    return "E_NOINTERFACE";
  default:
    return "(other)";
  }
}

void PrintHr(const char *what, HRESULT hr) {
  printf("%s -> 0x%08lX (%s)\n", what, (unsigned long)hr, HrName(hr));
}

int Incomplete(const char *why) {
  printf("handler4805: WALK-INCOMPLETE: %s\n", why);
  return 2;
}
int Incomplete(const char *why, HRESULT hr) {
  printf("handler4805: WALK-INCOMPLETE: %s (hr=0x%08lX %s)\n", why,
         (unsigned long)hr, HrName(hr));
  return 2;
}

// A minimal custom IDxcIncludeHandler. It recognises the configured
// candidate name(s) for the one include the repro uses and serves them from
// memory; anything else fails, so an unexpected candidate spelling is
// visible in the transcript rather than silently satisfied.
class MemoryIncludeHandler : public IDxcIncludeHandler {
  ULONG refs_ = 1;
  IDxcLibrary *lib_; // not owned; used only to wrap a blob

public:
  int loadCount = 0;
  explicit MemoryIncludeHandler(IDxcLibrary *lib) : lib_(lib) {}

  HRESULT STDMETHODCALLTYPE
  LoadSource(LPCWSTR pFilename, IDxcBlob **ppIncludeSource) override {
    std::string cand = Narrow(pFilename);
    printf("handler4805: LoadSource candidate: %s\n", cand.c_str());
    ++loadCount;
    // Accept the exact spelling the reporter used, and the same name with
    // Windows-style separators, however the front end normalised it -- but
    // NOT a bare basename match, which would silently satisfy any request
    // and hide a real "wrong candidate" finding.
    // The front end presents a candidate resolved relative to the including
    // file's own directory (observed empirically, e.g.
    // ".\repro-dir\Includes\Uniforms.hlsl"), not the bare spelling inside
    // the quotes. Match on a normalised suffix so the harness is robust to
    // the exact prefix while still rejecting an unrelated request.
    std::string norm = cand;
    for (auto &c : norm)
      if (c == '\\')
        c = '/';
    const std::string suffix = "Includes/Uniforms.hlsl";
    bool match = norm.size() >= suffix.size() &&
                norm.compare(norm.size() - suffix.size(), suffix.size(),
                            suffix) == 0;
    if (!match) {
      *ppIncludeSource = nullptr;
      return E_FAIL;
    }
    std::string content = IncludedFileContent();
    IDxcBlobEncoding *blob = nullptr;
    HRESULT hr = lib_->CreateBlobWithEncodingOnHeapCopy(
        content.data(), (UINT32)content.size(), CP_UTF8, &blob);
    if (FAILED(hr) || !blob) {
      *ppIncludeSource = nullptr;
      return E_FAIL;
    }
    *ppIncludeSource = blob;
    return S_OK;
  }

  HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid,
                                           void **ppv) override {
    if (riid == __uuidof(IDxcIncludeHandler) || riid == __uuidof(IUnknown)) {
      *ppv = static_cast<IDxcIncludeHandler *>(this);
      AddRef();
      return S_OK;
    }
    *ppv = nullptr;
    return E_NOINTERFACE;
  }
  ULONG STDMETHODCALLTYPE AddRef() override { return ++refs_; }
  ULONG STDMETHODCALLTYPE Release() override {
    ULONG r = --refs_;
    if (r == 0)
      delete this;
    return r;
  }
};

} // namespace

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--version") || !strcmp(argv[i], "-version")) {
      const char *dll = getenv("DXC_INCLUDE_DLL");
      printf("handler4805 harness for issue 4805; DXC_INCLUDE_DLL=%s\n",
             dll ? dll : "(unset)");
      return 0;
    }
  }

  const char *dllEnv = getenv("DXC_INCLUDE_DLL");
  if (!dllEnv || !*dllEnv) {
    fprintf(stderr, "handler4805: set DXC_INCLUDE_DLL to a dxcompiler.dll\n");
    return 3;
  }

  std::wstring profile, entry;
  std::string source, outPath;
  std::vector<std::wstring> extra;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if ((a == "-T" || a == "/T") && i + 1 < argc)
      profile = Widen(argv[++i]);
    else if ((a == "-E" || a == "/E") && i + 1 < argc)
      entry = Widen(argv[++i]);
    else if ((a == "-Fo" || a == "/Fo") && i + 1 < argc)
      outPath = argv[++i];
    else if (a.size() >= 5 && a.compare(a.size() - 5, 5, ".hlsl") == 0 &&
             a[0] != '-' && a[0] != '/')
      source = a;
    else
      extra.push_back(Widen(a));
  }
  if (source.empty() || profile.empty()) {
    fprintf(stderr,
            "handler4805: usage: handler4805 -T <profile> [-E <entry>] "
            "[-Fo <out.spv>] <extra dxc args...> <source.hlsl>\n");
    return 3;
  }
  if (entry.empty())
    entry = L"main";

  printf("# handler4805: #4805 custom include handler probe\n");
  printf("source: %s\n", source.c_str());
  printf("marker: %s\n", kIncludeMarker);

  HMODULE mod = LoadLibraryW(Widen(dllEnv).c_str());
  if (!mod)
    return Incomplete("LoadLibraryW failed on DXC_INCLUDE_DLL");
  auto createInstance =
      (DxcCreateInstanceProc)GetProcAddress(mod, "DxcCreateInstance");
  if (!createInstance)
    return Incomplete("no DxcCreateInstance export in DXC_INCLUDE_DLL");

  IDxcLibrary *lib = nullptr;
  HRESULT hr =
      createInstance(CLSID_DxcLibrary, __uuidof(IDxcLibrary), (void **)&lib);
  if (FAILED(hr) || !lib)
    return Incomplete("DxcCreateInstance(CLSID_DxcLibrary) failed", hr);

  IDxcBlobEncoding *src = nullptr;
  hr = lib->CreateBlobFromFile(Widen(source).c_str(), nullptr, &src);
  if (FAILED(hr) || !src)
    return Incomplete("CreateBlobFromFile failed (is the source there?)", hr);

  IDxcCompiler *comp = nullptr;
  hr = createInstance(CLSID_DxcCompiler, __uuidof(IDxcCompiler), (void **)&comp);
  if (FAILED(hr) || !comp)
    return Incomplete("DxcCreateInstance(CLSID_DxcCompiler) failed", hr);

  MemoryIncludeHandler *handler = new MemoryIncludeHandler(lib);

  std::vector<LPCWSTR> args;
  for (auto &s : extra)
    args.push_back(s.c_str());

  IDxcOperationResult *res = nullptr;
  hr = comp->Compile(src, Widen(source).c_str(), entry.c_str(), profile.c_str(),
                     args.empty() ? nullptr : args.data(), (UINT32)args.size(),
                     nullptr, 0, handler, &res);
  if (FAILED(hr) || !res) {
    printf("handler4805: LoadSource call count: %d\n", handler->loadCount);
    return Incomplete("IDxcCompiler::Compile call failed", hr);
  }

  HRESULT status = E_FAIL;
  res->GetStatus(&status);
  PrintHr("IDxcCompiler::Compile status", status);
  printf("handler4805: LoadSource call count: %d\n", handler->loadCount);

  IDxcBlobEncoding *errs = nullptr;
  if (SUCCEEDED(res->GetErrorBuffer(&errs)) && errs &&
      errs->GetBufferSize() > 1) {
    printf("compiler diagnostics:\n%.*s\n", (int)errs->GetBufferSize(),
           (const char *)errs->GetBufferPointer());
  }
  if (FAILED(status))
    return Incomplete("the shader did not compile; see diagnostics above");

  IDxcBlob *container = nullptr;
  if (FAILED(res->GetResult(&container)) || !container)
    return Incomplete("no container blob from a successful compile");

  printf("container bytes: %llu\n",
         (unsigned long long)container->GetBufferSize());

  if (!outPath.empty()) {
    HANDLE hf = CreateFileW(Widen(outPath).c_str(), GENERIC_WRITE, 0, nullptr,
                            CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (hf == INVALID_HANDLE_VALUE)
      return Incomplete("could not open -Fo output for writing");
    DWORD written = 0;
    WriteFile(hf, container->GetBufferPointer(),
             (DWORD)container->GetBufferSize(), &written, nullptr);
    CloseHandle(hf);
    printf("wrote: %s (%lu bytes)\n", outPath.c_str(), written);
  }

  // Byte search over the raw container: does the marker appear verbatim?
  const char *data = (const char *)container->GetBufferPointer();
  size_t size = (size_t)container->GetBufferSize();
  std::string haystack(data, size);
  bool markerPresent = haystack.find(kIncludeMarker) != std::string::npos;
  printf("marker-present-in-container: %s\n",
         markerPresent ? "YES" : "NO");

  printf("handler4805: RESULT-COMPLETE\n");
  return 0;
}
