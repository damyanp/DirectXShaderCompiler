// refl3237 -- #3237 "Library Reflection: Listing parameters return E_FAIL"
//
// The defect is in the reflection API, not in anything dxc.exe prints:
// ID3D12FunctionParameterReflection::GetDesc returns E_FAIL. dxc.exe never
// calls that interface, so `cmd.txt` alone cannot reach the code under test.
// This harness is registered as a compiler (SKILL.md, "When the symptom is in
// a pass dxc.exe cannot run, register the harness as a compiler") so that
// `triage.py run`, --shader/--args controls, --expect and `reindex` all keep
// working on it.
//
// It takes dxc-style arguments and does, in one process, what the issue body
// does in the reporter's application:
//
//   IDxcCompiler::Compile(source, -T <profile>)     -> a library container
//   IDxcContainerReflection::Load / FindFirstPartKind(DXIL)
//   GetPartReflection(idx, IID_ID3D12LibraryReflection)
//   ID3D12LibraryReflection::GetDesc                -> FunctionCount
//   ID3D12LibraryReflection::GetFunctionByIndex(0)
//   ID3D12FunctionReflection::GetDesc               -> D3D12_FUNCTION_DESC
//   ID3D12FunctionReflection::GetFunctionParameter(0)
//   ID3D12FunctionParameterReflection::GetDesc      <-- the reported E_FAIL
//
// EVERY interface here is implemented inside dxcompiler.dll, so pointing
// DXC_REFLECT_DLL at a release's dxcompiler.dll measures THAT RELEASE's
// reflection implementation -- the same device as #2922/#2923's
// `dxopt -external`. No GPU, driver or D3D runtime is involved.
//
//   set DXC_REFLECT_DLL=<...>\dxcompiler.dll
//   refl3237.exe -T lib_6_3 repro.hlsl
//
// SELF-CONSISTENCY (SKILL.md, "A control cannot catch a broken reader",
// measured on #2923): a harness that can return "nothing here" and "nothing
// matched" through the same channel will eventually be believed. So this one
// never prints the RESULT line unless the whole walk completed; any earlier
// failure prints a loud `refl3237: WALK-INCOMPLETE:` marker and exits 2. It
// also echoes the mangled function name, which is the strongest available
// check that the vtable walk landed on the right slots -- a wrong vtable
// index cannot produce a correct C++ mangled name.
//
// The HRESULT this harness reports is an API return value. It is deliberately
// NOT folded into the process exit code, because dxc.exe returns the same
// numeric value (E_FAIL, 0x80004005) for ordinary diagnosed errors and the two
// must not be conflated. Exit 0 means "the walk completed", not "no bug".

#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "dxc/dxcapi.h"

#include "d3d12shader.h"

namespace {

// DxilContainer.h's DFCC_DXIL, spelled out so this file needs only dxcapi.h.
const UINT32 kFourCC_DXIL = DXC_FOURCC('D', 'X', 'I', 'L');

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

void PrintHr(const char *what, HRESULT hr) {
  printf("%s -> 0x%08lX (%s)\n", what, (unsigned long)hr, HrName(hr));
}

// Rewrite an absolute path to the placeholders triage.py uses in its own
// capture headers: <cache>, <triage>, <repo>, most specific first, forward
// slashes. This output is committed, so a raw path would ship one machine's
// directory layout to everyone and make the artifact non-portable. triage.py
// redacts the lines IT writes, but the transcript below is our stdout and
// passes through untouched -- so the redaction has to happen here.
//
// The roots are derived from this executable's own location rather than from
// the environment, so the rule holds however the harness is invoked:
//   <triage>/data/issues/3237/bin/refl3237.exe
//    ^repo../..    <triage> is 5 pops up, <repo> 3 more.
std::string Redact(const std::string &path) {
  wchar_t selfw[MAX_PATH * 4] = {0};
  DWORD n = GetModuleFileNameW(nullptr, selfw, MAX_PATH * 4);
  if (!n || n >= MAX_PATH * 4)
    return path;
  int bytes =
      WideCharToMultiByte(CP_UTF8, 0, selfw, -1, nullptr, 0, nullptr, nullptr);
  if (bytes <= 0)
    return path;
  std::string self(bytes - 1, '\0');
  WideCharToMultiByte(CP_UTF8, 0, selfw, -1, &self[0], bytes, nullptr, nullptr);
  for (auto &c : self)
    if (c == '\\')
      c = '/';
  std::string p = path;
  for (auto &c : p)
    if (c == '\\')
      c = '/';

  auto up = [](std::string s, int n) {
    for (int i = 0; i < n; ++i) {
      size_t slash = s.find_last_of('/');
      if (slash == std::string::npos)
        return std::string();
      s.erase(slash);
    }
    return s;
  };
  std::string triage = up(self, 5); // strip refl3237.exe/bin/3237/issues/data
  if (triage.empty())
    return path;
  std::string repo = up(triage, 3); // strip dxc-issue-triage/skills/.github

  const std::pair<std::string, const char *> roots[] = {
      {triage + "/.cache", "<cache>"}, {triage, "<triage>"}, {repo, "<repo>"}};
  for (const auto &r : roots) {
    if (r.first.empty() || p.size() <= r.first.size())
      continue;
    if (_strnicmp(p.c_str(), r.first.c_str(), r.first.size()) == 0 &&
        p[r.first.size()] == '/')
      return std::string(r.second) + p.substr(r.first.size());
  }
  return p;
}

int Incomplete(const char *why) {
  printf("refl3237: WALK-INCOMPLETE: %s\n", why);
  return 2;
}

// An aborted walk that hides the HRESULT is a row nobody can act on later:
// "IDxcCompiler::Compile call failed" on one old release cost a round trip
// before this overload existed. Carry the number.
int Incomplete(const char *why, HRESULT hr) {
  printf("refl3237: WALK-INCOMPLETE: %s (hr=0x%08lX %s)\n", why,
         (unsigned long)hr, HrName(hr));
  return 2;
}

std::wstring Widen(const char *s) {
  int n = MultiByteToWideChar(CP_UTF8, 0, s, -1, nullptr, 0);
  std::wstring w(n ? n - 1 : 0, L'\0');
  if (n)
    MultiByteToWideChar(CP_UTF8, 0, s, -1, &w[0], n);
  return w;
}

// D3D12_FUNCTION_DESC has no length field for Name, and the DXIL library
// mangling begins with a literal 0x01 byte. Print it in a form a reader can
// compare against the issue body without a hex editor.
std::string Escape(const char *s) {
  std::string out;
  if (!s)
    return "(null)";
  for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
    if (*p == 0x01)
      out += "\\x01";
    else if (*p < 0x20 || *p >= 0x7F) {
      char buf[8];
      sprintf_s(buf, "\\x%02X", *p);
      out += buf;
    } else
      out += (char)*p;
  }
  return out;
}

const char *SvtName(D3D_SHADER_VARIABLE_TYPE t) {
  switch (t) {
  case D3D_SVT_VOID:
    return "D3D_SVT_VOID";
  case D3D_SVT_BOOL:
    return "D3D_SVT_BOOL";
  case D3D_SVT_INT:
    return "D3D_SVT_INT";
  case D3D_SVT_FLOAT:
    return "D3D_SVT_FLOAT";
  case D3D_SVT_UINT:
    return "D3D_SVT_UINT";
  default:
    return "(other)";
  }
}

} // namespace

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--version") || !strcmp(argv[i], "-version")) {
      // `triage.py compiler` records this, and it must identify the DLL under
      // test, not the harness -- the harness is inert plumbing.
      const char *dll = getenv("DXC_REFLECT_DLL");
      printf("refl3237 harness for issue 3237; DXC_REFLECT_DLL=%s\n",
             dll ? Redact(dll).c_str() : "(unset)");
      return 0;
    }
  }

  const char *dllEnv = getenv("DXC_REFLECT_DLL");
  if (!dllEnv || !*dllEnv) {
    fprintf(stderr, "refl3237: set DXC_REFLECT_DLL to a dxcompiler.dll\n");
    return 3;
  }

  std::wstring profile, entry;
  std::string source;
  std::vector<std::wstring> extra;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if ((a == "-T" || a == "/T") && i + 1 < argc)
      profile = Widen(argv[++i]);
    else if ((a == "-E" || a == "/E") && i + 1 < argc)
      entry = Widen(argv[++i]);
    else if (a.size() >= 5 && a.compare(a.size() - 5, 5, ".hlsl") == 0 &&
             a[0] != '-' && a[0] != '/')
      // Identify the source by suffix, not by "does not start with a dash".
      // Flags take separate values -- `-default-linkage external` -- and
      // treating `external` as the filename silently compiles nothing while
      // looking like an ordinary argument error.
      source = a;
    else
      extra.push_back(Widen(argv[i]));
  }
  if (source.empty() || profile.empty()) {
    fprintf(stderr, "refl3237: usage: refl3237 -T <profile> [-E <entry>] "
                    "<source.hlsl>\n");
    return 3;
  }
  if (entry.empty()) {
    // dxc.exe always passes an entry point (its own default is `main`), and
    // v1.4.1907's dxcompiler.dll rejects a null pEntryPoint with E_INVALIDARG
    // even for a lib_* profile, where the value is then ignored. Passing null
    // would have silently dropped the oldest release out of the history as an
    // invalid probe and made the defect look newer than it is.
    entry = L"main";
  }

  printf("# refl3237: #3237 library-reflection parameter probe\n");
  printf("dll: %s\n", Redact(dllEnv).c_str());
  printf("source: %s\n", source.c_str());

  HMODULE mod = LoadLibraryW(Widen(dllEnv).c_str());
  if (!mod)
    return Incomplete("LoadLibraryW failed on DXC_REFLECT_DLL");
  auto createInstance =
      (DxcCreateInstanceProc)GetProcAddress(mod, "DxcCreateInstance");
  if (!createInstance)
    return Incomplete("no DxcCreateInstance export in DXC_REFLECT_DLL");

  IDxcLibrary *lib = nullptr;
  HRESULT hr = createInstance(CLSID_DxcLibrary, __uuidof(IDxcLibrary),
                              (void **)&lib);
  if (FAILED(hr) || !lib)
    return Incomplete("DxcCreateInstance(CLSID_DxcLibrary) failed");

  IDxcBlobEncoding *src = nullptr;
  hr = lib->CreateBlobFromFile(Widen(source.c_str()).c_str(), nullptr, &src);
  if (FAILED(hr) || !src)
    return Incomplete("CreateBlobFromFile failed (is the source there?)");

  IDxcCompiler *comp = nullptr;
  hr = createInstance(CLSID_DxcCompiler, __uuidof(IDxcCompiler),
                      (void **)&comp);
  if (FAILED(hr) || !comp)
    return Incomplete("DxcCreateInstance(CLSID_DxcCompiler) failed");

  std::vector<LPCWSTR> args;
  for (auto &s : extra)
    args.push_back(s.c_str());

  IDxcOperationResult *res = nullptr;
  hr = comp->Compile(src, Widen(source.c_str()).c_str(),
                     entry.empty() ? nullptr : entry.c_str(), profile.c_str(),
                     args.empty() ? nullptr : args.data(), (UINT32)args.size(),
                     nullptr, 0, nullptr, &res);
  if (FAILED(hr) || !res)
    return Incomplete("IDxcCompiler::Compile call failed", hr);

  HRESULT status = E_FAIL;
  res->GetStatus(&status);
  PrintHr("IDxcCompiler::Compile status", status);

  IDxcBlobEncoding *errs = nullptr;
  if (SUCCEEDED(res->GetErrorBuffer(&errs)) && errs &&
      errs->GetBufferSize() > 1) {
    printf("compiler diagnostics:\n%.*s\n", (int)errs->GetBufferSize(),
           (const char *)errs->GetBufferPointer());
  }
  if (FAILED(status))
    return Incomplete("the library did not compile; see diagnostics above");

  IDxcBlob *container = nullptr;
  if (FAILED(res->GetResult(&container)) || !container)
    return Incomplete("no container blob from a successful compile");

  IDxcContainerReflection *cr = nullptr;
  hr = createInstance(CLSID_DxcContainerReflection,
                      __uuidof(IDxcContainerReflection), (void **)&cr);
  if (FAILED(hr) || !cr)
    return Incomplete("DxcCreateInstance(CLSID_DxcContainerReflection) failed");

  hr = cr->Load(container);
  PrintHr("IDxcContainerReflection::Load", hr);
  if (FAILED(hr))
    return Incomplete("could not load the container for reflection");

  UINT32 idx = 0;
  hr = cr->FindFirstPartKind(kFourCC_DXIL, &idx);
  PrintHr("IDxcContainerReflection::FindFirstPartKind(DXIL)", hr);
  if (FAILED(hr))
    return Incomplete("container has no DXIL part");

  ID3D12LibraryReflection *libRefl = nullptr;
  hr = cr->GetPartReflection(idx, __uuidof(ID3D12LibraryReflection),
                             (void **)&libRefl);
  PrintHr("IDxcContainerReflection::GetPartReflection(ID3D12LibraryReflection)",
          hr);
  if (FAILED(hr) || !libRefl)
    return Incomplete("this DXIL part does not expose ID3D12LibraryReflection "
                      "(not a library?)");

  D3D12_LIBRARY_DESC libDesc = {};
  hr = libRefl->GetDesc(&libDesc);
  PrintHr("ID3D12LibraryReflection::GetDesc", hr);
  if (FAILED(hr))
    return Incomplete("ID3D12LibraryReflection::GetDesc failed");
  printf("  D3D12_LIBRARY_DESC.FunctionCount=%u\n", libDesc.FunctionCount);
  if (libDesc.FunctionCount == 0)
    return Incomplete("the library reflects zero functions");

  ID3D12FunctionReflection *fn = libRefl->GetFunctionByIndex(0);
  printf("ID3D12LibraryReflection::GetFunctionByIndex(0) -> %s\n",
         fn ? "non-null" : "NULL");
  if (!fn)
    return Incomplete("GetFunctionByIndex(0) returned NULL");

  D3D12_FUNCTION_DESC fd = {};
  hr = fn->GetDesc(&fd);
  PrintHr("ID3D12FunctionReflection::GetDesc", hr);
  if (FAILED(hr))
    return Incomplete("ID3D12FunctionReflection::GetDesc failed");

  // Populated fields and unpopulated ones, from the same call, side by side.
  printf("  D3D12_FUNCTION_DESC.Name=\"%s\"\n", Escape(fd.Name).c_str());
  printf("  D3D12_FUNCTION_DESC.Version=0x%08X\n", fd.Version);
  printf("  D3D12_FUNCTION_DESC.ConstantBuffers=%u\n", fd.ConstantBuffers);
  printf("  D3D12_FUNCTION_DESC.BoundResources=%u\n", fd.BoundResources);
  printf("  D3D12_FUNCTION_DESC.RequiredFeatureFlags=0x%llX\n",
         (unsigned long long)fd.RequiredFeatureFlags);
  printf("  D3D12_FUNCTION_DESC.FunctionParameterCount=%d\n",
         fd.FunctionParameterCount);
  printf("  D3D12_FUNCTION_DESC.HasReturn=%s\n",
         fd.HasReturn ? "TRUE" : "FALSE");

  // The reported call, verbatim from the issue body.
  ID3D12FunctionParameterReflection *p0 = fn->GetFunctionParameter(0);
  printf("ID3D12FunctionReflection::GetFunctionParameter(0) -> %s\n",
         p0 ? "non-null" : "NULL");
  if (!p0)
    return Incomplete("GetFunctionParameter(0) returned NULL");

  D3D12_PARAMETER_DESC pd = {};
  HRESULT hrParam0 = p0->GetDesc(&pd);
  PrintHr("ID3D12FunctionParameterReflection::GetDesc(param 0)", hrParam0);
  if (SUCCEEDED(hrParam0)) {
    printf("  D3D12_PARAMETER_DESC.Name=\"%s\"\n", Escape(pd.Name).c_str());
    printf("  D3D12_PARAMETER_DESC.SemanticName=\"%s\"\n",
           Escape(pd.SemanticName).c_str());
    printf("  D3D12_PARAMETER_DESC.Type=%s\n", SvtName(pd.Type));
    printf("  D3D12_PARAMETER_DESC.Rows=%u Columns=%u\n", pd.Rows, pd.Columns);
    printf("  D3D12_PARAMETER_DESC.Flags=0x%X\n", (unsigned)pd.Flags);
  }

  // D3D_RETURN_PARAMETER_INDEX is the documented way to ask for the return
  // value, and the header comments in both d3d12shader.h and DXC's own
  // implementation call it out. Asking for it separates "index 0 is wrong" from
  // "no index works".
  ID3D12FunctionParameterReflection *pr =
      fn->GetFunctionParameter(D3D_RETURN_PARAMETER_INDEX);
  D3D12_PARAMETER_DESC rd = {};
  HRESULT hrRet = pr ? pr->GetDesc(&rd) : E_POINTER;
  PrintHr("ID3D12FunctionParameterReflection::GetDesc(D3D_RETURN_PARAMETER_"
          "INDEX)",
          hrRet);

  // Self-checks. The mangled name is the load-bearing one: a mis-indexed
  // vtable cannot produce a correct C++ mangled symbol.
  bool nameOk = fd.Name && strstr(fd.Name, "Apply") != nullptr;
  printf("SELFCHECK: reached-parameter-getdesc=yes\n");
  printf("SELFCHECK: function-name-contains-Apply=%s\n", nameOk ? "yes" : "no");
  if (!nameOk)
    printf("refl3237: PARSE-WARNING: the reflected function name does not "
           "contain \"Apply\"; the walk may not be reading what it thinks\n");

  printf("RESULT: PARAM0-GETDESC=0x%08lX RETURN-GETDESC=0x%08lX "
         "PARAMCOUNT=%d\n",
         (unsigned long)hrParam0, (unsigned long)hrRet,
         fd.FunctionParameterCount);
  return 0;
}
