// refl2952 -- #2952 "Expose ray payload size / function type through
// Reflection"
//
// The report is about what a *reflection container* can tell an application,
// not about anything dxc.exe prints. dxc.exe never calls
// ID3D12LibraryReflection, so `cmd.txt` alone cannot reach the code under
// test. This harness is registered as a compiler (SKILL.md, "When the symptom
// is in a pass dxc.exe cannot run, register the harness as a compiler") so
// that `triage.py run`, --shader/--args controls, --expect and `reindex` all
// keep working on it.
//
// It answers the issue's two questions, and one the issue does not ask but
// which decides what the request actually costs:
//
//   Q1  can an application get the SHADER KIND (raygen, miss, ...) of an
//       exported function from the reflection API?
//   Q2  can it get the RAY PAYLOAD SIZE?
//   Q3  is the payload size IN THE CONTAINER AT ALL? If it is not, no
//       reflection-API change alone could expose it, and the request is a
//       much larger piece of work than it looks.
//
// Q1/Q2 are answered by walking exactly what an application has:
//
//   IDxcCompiler::Compile(source, -T lib_6_3)      -> a library container
//   IDxcContainerReflection::Load / FindFirstPartKind(DXIL)
//   GetPartReflection(idx, IID_ID3D12LibraryReflection)
//   ID3D12LibraryReflection::GetDesc               -> FunctionCount
//   ID3D12LibraryReflection::GetFunctionByIndex(i)
//   ID3D12FunctionReflection::GetDesc              -> D3D12_FUNCTION_DESC
//
// Q3 is answered from the RDAT part of the same container, read with DXC's own
// RDAT reader (include/dxc/DxilContainer/DxilRuntimeReflection.{h,inl}) rather
// than a hand-rolled parser -- SKILL.md, "A control cannot catch a broken
// reader" (#2923). Note what that means for provenance: the *reader* is always
// this repo's, while the *container* is produced by whichever dxcompiler.dll
// DXC_REFLECT_DLL names. That is the intended arrangement for Q3, which asks
// whether a release RECORDED the data, not whether it could read it back.
//
// EVERY interface used for Q1/Q2 is implemented inside dxcompiler.dll, so
// pointing DXC_REFLECT_DLL at a release's dxcompiler.dll measures THAT
// RELEASE's reflection implementation -- the same device as #3237's harness and
// #2922/#2923's `dxopt -external`. No GPU, driver or D3D runtime is involved.
//
//   set DXC_REFLECT_DLL=<...>\dxcompiler.dll
//   refl2952.exe -T lib_6_3 repro.hlsl
//
// SELF-CONSISTENCY (SKILL.md, "A control cannot catch a broken reader"): this
// harness never prints its RESULT line unless the whole walk completed; any
// earlier failure prints a loud `refl2952: WALK-INCOMPLETE:` marker and exits
// 2. It also cross-checks the reflection function list against the RDAT
// function list by name, and self-tests the field search that answers Q2 by
// looking for a value it knows is present -- a search that can only ever
// return "not found" would answer Q2 the same way whether or not the field
// exists.
//
// Exit 0 means "the walk completed", not "no bug". The observable is the
// content of the transcript.

#include <windows.h>

#include <cassert> // DxilRuntimeReflection.inl uses assert() but does not
                   // include <cassert> itself; it is normally compiled inside
                   // DXC, where something earlier in the TU has already pulled
                   // it in.
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "dxc/dxcapi.h"

#include "d3d12shader.h"

// DXC's own RDAT reader. Header-only: DxilRuntimeReflection.h pulls in
// DxilConstants.h, which needs only <stdint.h>. Including the .inl here gives
// the reader definitions in this single translation unit.
#include "dxc/DxilContainer/DxilRuntimeReflection.h"
#include "dxc/DxilContainer/DxilRuntimeReflection.inl"

namespace {

// DxilContainer.h's fourccs, spelled out so this file needs only dxcapi.h for
// the DXC API surface.
const UINT32 kFourCC_DXIL = DXC_FOURCC('D', 'X', 'I', 'L');
const UINT32 kFourCC_RDAT = DXC_FOURCC('R', 'D', 'A', 'T');

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

// hlsl::DXIL::ShaderKind, spelled for printing. The numbering is DXC's, and
// only values 0..5 coincide with d3d12shader.h's D3D12_SHADER_VERSION_TYPE --
// which is the crux of Q1 and is why this table is written out here rather
// than assumed to be a documented enum.
const char *KindName(unsigned k) {
  static const char *names[] = {
      "Pixel",         "Vertex",     "Geometry",      "Hull",
      "Domain",        "Compute",    "Library",       "RayGeneration",
      "Intersection",  "AnyHit",     "ClosestHit",    "Miss",
      "Callable",      "Mesh",       "Amplification", "Node"};
  if (k < sizeof(names) / sizeof(names[0]))
    return names[k];
  return "(unknown)";
}

// Rewrite an absolute path to the placeholders triage.py uses in its own
// capture headers: <cache>, <triage>, <repo>, most specific first, forward
// slashes. This output is committed, so a raw path would ship one machine's
// directory layout to everyone. triage.py redacts the lines IT writes; the
// transcript below is our stdout and passes through untouched, so the
// redaction has to happen here too (#3237's method note 8).
//
// Roots are derived from this executable's own location, so the rule holds
// however the harness is invoked:
//   <triage>/data/issues/2952/bin/refl2952.exe
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

  auto up = [](std::string s, int levels) {
    for (int i = 0; i < levels; ++i) {
      size_t slash = s.find_last_of('/');
      if (slash == std::string::npos)
        return std::string();
      s.erase(slash);
    }
    return s;
  };
  std::string triage = up(self, 5); // strip refl2952.exe/bin/2952/issues/data
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
  printf("refl2952: WALK-INCOMPLETE: %s\n", why);
  return 2;
}

// An aborted walk that hides the HRESULT is a row nobody can act on later
// (#3237's method note 4). Carry the number.
int Incomplete(const char *why, HRESULT hr) {
  printf("refl2952: WALK-INCOMPLETE: %s (hr=0x%08lX %s)\n", why,
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

// The DXIL library mangling begins with a literal 0x01 byte. Print it in a
// form a reader can compare against the RDAT dump without a hex editor.
std::string Escape(const char *s) {
  std::string out;
  if (!s)
    return "(null)";
  for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
    if (*p < 0x20 || *p >= 0x7F) {
      char buf[8];
      sprintf_s(buf, "\\x%02X", *p);
      out += buf;
    } else
      out += (char)*p;
  }
  return out;
}

struct Field {
  const char *name;
  unsigned long long value;
};

// Every numeric field of D3D12_FUNCTION_DESC, by name. Q2 is "can the payload
// size be retrieved", and the honest way to answer it is to enumerate what the
// struct actually carries and look, rather than to assert from the header that
// no such field exists.
std::vector<Field> DescFields(const D3D12_FUNCTION_DESC &d) {
  return {
      {"Version", d.Version},
      {"Flags", d.Flags},
      {"ConstantBuffers", d.ConstantBuffers},
      {"BoundResources", d.BoundResources},
      {"InstructionCount", d.InstructionCount},
      {"TempRegisterCount", d.TempRegisterCount},
      {"TempArrayCount", d.TempArrayCount},
      {"DefCount", d.DefCount},
      {"DclCount", d.DclCount},
      {"TextureNormalInstructions", d.TextureNormalInstructions},
      {"TextureLoadInstructions", d.TextureLoadInstructions},
      {"TextureCompInstructions", d.TextureCompInstructions},
      {"TextureBiasInstructions", d.TextureBiasInstructions},
      {"TextureGradientInstructions", d.TextureGradientInstructions},
      {"FloatInstructionCount", d.FloatInstructionCount},
      {"IntInstructionCount", d.IntInstructionCount},
      {"UintInstructionCount", d.UintInstructionCount},
      {"StaticFlowControlCount", d.StaticFlowControlCount},
      {"DynamicFlowControlCount", d.DynamicFlowControlCount},
      {"MacroInstructionCount", d.MacroInstructionCount},
      {"ArrayInstructionCount", d.ArrayInstructionCount},
      {"MovInstructionCount", d.MovInstructionCount},
      {"MovcInstructionCount", d.MovcInstructionCount},
      {"ConversionInstructionCount", d.ConversionInstructionCount},
      {"BitwiseInstructionCount", d.BitwiseInstructionCount},
      {"MinFeatureLevel", (unsigned long long)d.MinFeatureLevel},
      {"RequiredFeatureFlags", d.RequiredFeatureFlags},
      {"FunctionParameterCount",
       (unsigned long long)(unsigned)d.FunctionParameterCount},
      {"HasReturn", (unsigned long long)(unsigned)d.HasReturn},
      {"Has10Level9VertexShader",
       (unsigned long long)(unsigned)d.Has10Level9VertexShader},
      {"Has10Level9PixelShader",
       (unsigned long long)(unsigned)d.Has10Level9PixelShader},
  };
}

// Names of fields holding `want`, excluding those the caller says do not count
// as an answer. `Version` is excluded from a payload search because it holds
// the encoded shader model and kind and can collide numerically with a small
// byte size for no meaningful reason.
std::vector<const char *> FieldsHolding(const std::vector<Field> &fields,
                                        unsigned long long want,
                                        bool skipVersion) {
  std::vector<const char *> hits;
  for (const auto &f : fields) {
    if (skipVersion && !strcmp(f.name, "Version"))
      continue;
    if (f.value == want)
      hits.push_back(f.name);
  }
  return hits;
}

struct RdatEntry {
  unsigned kind = 16; // DXIL::ShaderKind::Invalid
  unsigned payload = 0;
  unsigned attrs = 0;
  bool seen = false;
};

} // namespace

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--version") || !strcmp(argv[i], "-version")) {
      // `triage.py compiler` records this, and it must identify the DLL under
      // test, not the harness -- the harness is inert plumbing.
      const char *dll = getenv("DXC_REFLECT_DLL");
      printf("refl2952 harness for issue 2952; DXC_REFLECT_DLL=%s\n",
             dll ? Redact(dll).c_str() : "(unset)");
      return 0;
    }
  }

  const char *dllEnv = getenv("DXC_REFLECT_DLL");
  if (!dllEnv || !*dllEnv) {
    fprintf(stderr, "refl2952: set DXC_REFLECT_DLL to a dxcompiler.dll\n");
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
      // Identify the source by suffix, not by "does not start with a dash":
      // flags take separate values, and treating one as the filename compiles
      // nothing while looking like an ordinary argument error (#3237).
      source = a;
    else
      extra.push_back(Widen(argv[i]));
  }
  if (source.empty() || profile.empty()) {
    fprintf(stderr, "refl2952: usage: refl2952 -T <profile> [-E <entry>] "
                    "<source.hlsl>\n");
    return 3;
  }
  if (entry.empty()) {
    // v1.4.1907's dxcompiler.dll rejects a null pEntryPoint with E_INVALIDARG
    // even for a lib_* profile where the value is then ignored; passing null
    // would silently drop the oldest release out of the history as an invalid
    // probe (#3237's method note 4).
    entry = L"main";
  }

  printf("# refl2952: #2952 ray payload size / shader kind through the "
         "reflection API\n");
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
  HRESULT hr =
      createInstance(CLSID_DxcLibrary, __uuidof(IDxcLibrary), (void **)&lib);
  if (FAILED(hr) || !lib)
    return Incomplete("DxcCreateInstance(CLSID_DxcLibrary) failed", hr);

  IDxcBlobEncoding *src = nullptr;
  hr = lib->CreateBlobFromFile(Widen(source.c_str()).c_str(), nullptr, &src);
  if (FAILED(hr) || !src)
    return Incomplete("CreateBlobFromFile failed (is the source there?)", hr);

  IDxcCompiler *comp = nullptr;
  hr = createInstance(CLSID_DxcCompiler, __uuidof(IDxcCompiler), (void **)&comp);
  if (FAILED(hr) || !comp)
    return Incomplete("DxcCreateInstance(CLSID_DxcCompiler) failed", hr);

  std::vector<LPCWSTR> args;
  for (auto &s : extra)
    args.push_back(s.c_str());

  IDxcOperationResult *res = nullptr;
  hr = comp->Compile(src, Widen(source.c_str()).c_str(), entry.c_str(),
                     profile.c_str(), args.empty() ? nullptr : args.data(),
                     (UINT32)args.size(), nullptr, 0, nullptr, &res);
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
    return Incomplete("DxcCreateInstance(CLSID_DxcContainerReflection) failed",
                      hr);

  hr = cr->Load(container);
  PrintHr("IDxcContainerReflection::Load", hr);
  if (FAILED(hr))
    return Incomplete("could not load the container for reflection", hr);

  // ---------------------------------------------------------------- Q3 ----
  // What the container records. Read first, because the payload sizes it
  // reports are the values the API search below looks for -- deriving them
  // from the container rather than hardcoding them keeps a control shader with
  // a different payload size honest without editing this file.
  printf("\n--- RDAT part: what the container records ---\n");
  std::map<std::string, RdatEntry> byName;
  UINT32 rdatIdx = 0;
  bool rdatRead = false;
  unsigned rdatFuncCount = 0;
  hr = cr->FindFirstPartKind(kFourCC_RDAT, &rdatIdx);
  PrintHr("IDxcContainerReflection::FindFirstPartKind(RDAT)", hr);
  if (SUCCEEDED(hr)) {
    IDxcBlob *rdatBlob = nullptr;
    hr = cr->GetPartContent(rdatIdx, &rdatBlob);
    if (SUCCEEDED(hr) && rdatBlob) {
      hlsl::RDAT::DxilRuntimeData rdat;
      if (rdat.InitFromRDAT(rdatBlob->GetBufferPointer(),
                            rdatBlob->GetBufferSize())) {
        auto table = rdat.GetFunctionTable();
        rdatFuncCount = table.Count();
        rdatRead = true;
        printf("  RDAT part size=%u bytes, FunctionTable[%u]\n",
               (unsigned)rdatBlob->GetBufferSize(), rdatFuncCount);
        for (unsigned i = 0; i < rdatFuncCount; ++i) {
          auto f = table[i];
          RdatEntry e;
          e.kind = (unsigned)f.getShaderKind();
          e.payload = f.getPayloadSizeInBytes();
          e.attrs = f.getAttributeSizeInBytes();
          e.seen = true;
          const char *mangled = f.getName();
          const char *unmangled = f.getUnmangledName();
          if (mangled)
            byName[mangled] = e;
          printf("  [%u] %-18s RuntimeDataFunctionInfo.ShaderKind=%u (%s) "
                 ".PayloadSizeInBytes=%u .AttributeSizeInBytes=%u\n",
                 i, unmangled ? unmangled : "(null)", e.kind, KindName(e.kind),
                 e.payload, e.attrs);
        }
      } else {
        printf("  RDAT part present (%u bytes) but this repo's RDAT reader "
               "could not parse it\n",
               (unsigned)rdatBlob->GetBufferSize());
      }
    } else {
      PrintHr("IDxcContainerReflection::GetPartContent(RDAT)", hr);
    }
  } else {
    printf("  no RDAT part in this container\n");
  }
  if (!rdatRead)
    return Incomplete("could not read the RDAT part, so the payload sizes this "
                      "shader declares are unknown and the API search below "
                      "would have nothing to look for");

  // ------------------------------------------------------------- Q1/Q2 ----
  UINT32 idx = 0;
  hr = cr->FindFirstPartKind(kFourCC_DXIL, &idx);
  PrintHr("IDxcContainerReflection::FindFirstPartKind(DXIL)", hr);
  if (FAILED(hr))
    return Incomplete("container has no DXIL part", hr);

  ID3D12LibraryReflection *libRefl = nullptr;
  hr = cr->GetPartReflection(idx, __uuidof(ID3D12LibraryReflection),
                             (void **)&libRefl);
  PrintHr("IDxcContainerReflection::GetPartReflection(ID3D12LibraryReflection)",
          hr);
  if (FAILED(hr) || !libRefl)
    return Incomplete("this DXIL part does not expose ID3D12LibraryReflection "
                      "(not a library?)",
                      hr);

  D3D12_LIBRARY_DESC libDesc = {};
  hr = libRefl->GetDesc(&libDesc);
  PrintHr("ID3D12LibraryReflection::GetDesc", hr);
  if (FAILED(hr))
    return Incomplete("ID3D12LibraryReflection::GetDesc failed", hr);
  printf("  D3D12_LIBRARY_DESC.FunctionCount=%u\n", libDesc.FunctionCount);
  if (libDesc.FunctionCount == 0)
    return Incomplete("the library reflects zero functions");

  printf("\n--- D3D12 reflection API: what an application can see ---\n");
  unsigned kindAgree = 0, kindChecked = 0;
  unsigned payloadEntries = 0, payloadFound = 0;
  unsigned namesMatched = 0;
  bool searchSelftestPass = false;

  for (UINT i = 0; i < libDesc.FunctionCount; ++i) {
    ID3D12FunctionReflection *fn = libRefl->GetFunctionByIndex((INT)i);
    if (!fn)
      return Incomplete("GetFunctionByIndex returned NULL");
    D3D12_FUNCTION_DESC fd = {};
    HRESULT hrFn = fn->GetDesc(&fd);
    printf("[%u] ID3D12FunctionReflection::GetDesc -> 0x%08lX (%s)\n", i,
           (unsigned long)hrFn, HrName(hrFn));
    if (FAILED(hrFn))
      return Incomplete("ID3D12FunctionReflection::GetDesc failed", hrFn);

    std::string name = fd.Name ? fd.Name : "";
    unsigned apiKind = (fd.Version >> 16) & 0xFFFF;
    printf("    D3D12_FUNCTION_DESC.Name=\"%s\"\n", Escape(fd.Name).c_str());
    printf("    D3D12_FUNCTION_DESC.Version=0x%08X -> D3D12_SHVER_GET_TYPE=%u "
           "(%s), sm %u.%u\n",
           fd.Version, apiKind, KindName(apiKind), (fd.Version >> 4) & 0xF,
           fd.Version & 0xF);

    auto fields = DescFields(fd);
    std::string dump;
    for (const auto &f : fields) {
      char buf[128];
      sprintf_s(buf, "%s=%llu ", f.name, f.value);
      dump += buf;
    }
    printf("    all D3D12_FUNCTION_DESC numeric fields: %s\n", dump.c_str());

    auto it = byName.find(name);
    if (it == byName.end()) {
      printf("    refl2952: PARSE-WARNING: no RDAT record named \"%s\"; the "
             "two walks are not describing the same function\n",
             Escape(fd.Name).c_str());
      continue;
    }
    ++namesMatched;
    const RdatEntry &e = it->second;
    printf("    rdat: ShaderKind=%u (%s) PayloadSizeInBytes=%u "
           "AttributeSizeInBytes=%u\n",
           e.kind, KindName(e.kind), e.payload, e.attrs);

    ++kindChecked;
    bool kindOk = (apiKind == e.kind);
    if (kindOk)
      ++kindAgree;
    printf("    KIND: api=%s rdat=%s -> %s\n", KindName(apiKind),
           KindName(e.kind), kindOk ? "agree" : "DISAGREE");

    // The field search that answers Q2, plus the self-test that proves the
    // search can succeed at all. Searching for BoundResources' own value must
    // find BoundResources; a search that can only return "not found" would
    // answer Q2 identically whether or not a payload field existed.
    auto selftest = FieldsHolding(fields, fd.BoundResources, true);
    bool selfOk = false;
    for (const char *n : selftest)
      if (!strcmp(n, "BoundResources"))
        selfOk = true;
    if (selfOk)
      searchSelftestPass = true;

    if (e.payload == 0) {
      printf("    PAYLOAD: rdat says this entry carries no payload; nothing to "
             "search for\n");
      continue;
    }
    ++payloadEntries;
    auto hits = FieldsHolding(fields, e.payload, true);
    if (hits.empty()) {
      printf("    PAYLOAD: no field of D3D12_FUNCTION_DESC holds %u\n",
             e.payload);
    } else {
      ++payloadFound;
      std::string names;
      for (const char *n : hits) {
        names += n;
        names += " ";
      }
      printf("    PAYLOAD: %u appears in D3D12_FUNCTION_DESC field(s): %s\n",
             e.payload, names.c_str());
    }
  }

  printf("\nSELFCHECK: library-function-count=%u rdat-function-count=%u "
         "names-matched=%u\n",
         libDesc.FunctionCount, rdatFuncCount, namesMatched);
  printf("SELFCHECK: field-search-selftest=%s\n",
         searchSelftestPass ? "pass" : "FAIL");
  if (!searchSelftestPass)
    printf("refl2952: PARSE-WARNING: the D3D12_FUNCTION_DESC field search "
           "never found a value it knows is present; a negative PAYLOAD result "
           "below would be meaningless\n");
  if (namesMatched == 0)
    return Incomplete("no reflected function matched an RDAT record");

  const char *apiKindVerdict = kindChecked == 0            ? "n/a"
                               : kindAgree == kindChecked  ? "available"
                                                           : "wrong";
  const char *apiPayloadVerdict = payloadEntries == 0     ? "n/a"
                                  : payloadFound == 0     ? "unavailable"
                                                          : "available";

  printf("SUMMARY: payload-carrying-entries=%u api-payload-found=%u "
         "kind-checked=%u kind-agrees=%u\n",
         payloadEntries, payloadFound, kindChecked, kindAgree);
  printf("RESULT: API-SHADER-KIND=%s API-PAYLOAD-SIZE=%s RDAT-SHADER-KIND=%s "
         "RDAT-PAYLOAD-SIZE=%s\n",
         apiKindVerdict, apiPayloadVerdict, rdatRead ? "present" : "absent",
         payloadEntries ? "present" : "n/a");
  return 0;
}
