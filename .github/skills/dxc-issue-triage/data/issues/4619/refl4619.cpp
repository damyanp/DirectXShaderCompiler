// refl4619 -- #4619 "How to get thread group size and output primitive
// topology in MeshShader?"
//
// The question is about ID3D12ShaderReflection, which dxc.exe never calls, so
// `cmd.txt` alone cannot reach the code under test. `dxa -dumpreflection`
// cannot either: D3DReflectionDumper::Dump(D3D12_SHADER_DESC&) never calls
// GetThreadGroupSize at all, and prints GSOutputTopology only inside its
// `ShaderKind == Geometry` branch (lib/DxilContainer/D3DReflectionDumper.cpp).
// An absent field proves nothing if the dumper never calls the accessor
// (SKILL.md), so this harness calls them directly.
//
// Registered as a compiler (SKILL.md, "When the symptom is in a pass dxc.exe
// cannot run, register the harness as a compiler") so that `triage.py run`,
// --shader/--args controls, --expect and `reindex` keep working on it.
//
//   set DXC_REFLECT_DLL=<...>\dxcompiler.dll
//   refl4619.exe -T ms_6_5 -E main repro.hlsl
//
// EVERY interface here is implemented inside dxcompiler.dll, so pointing
// DXC_REFLECT_DLL at a release's dxcompiler.dll measures THAT RELEASE's
// reflection implementation. No GPU, driver or D3D runtime is involved.
//
// It answers both halves of the issue in one run:
//
//   (A) ID3D12ShaderReflection::GetThreadGroupSize(&x,&y,&z)  <- reported 0,0,0
//   (B) every topology-bearing field of D3D12_SHADER_DESC, plus
//       ID3D12ShaderReflection::GetGSInputPrimitive
//
// ...and then reads the SAME facts straight out of the container, bypassing
// ID3D12ShaderReflection entirely, so an absence on the API surface can be
// distinguished from the information simply not being recorded:
//
//   PSV0 / PSVRuntimeInfo1::MS1.MeshOutputTopology   <- the output topology
//   PSV0 / PSVRuntimeInfo2::NumThreadsX/Y/Z          <- the thread group size
//   the DXIL disassembly's numthreads metadata tuple
//
// SELF-CONSISTENCY (SKILL.md, "A control cannot catch a broken reader"): the
// RESULT line is never printed unless the whole walk completed. Any earlier
// failure prints a loud `refl4619: WALK-INCOMPLETE:` marker and exits 2, so
// "nothing here" and "nothing matched" cannot arrive through the same channel.
// The container-side reads are the reader self-test for the API-side reads:
// they are produced by different code on the same run, and the numthreads
// values (32,2,1) are distinct and non-unit, so a harness that returned a
// constant or swapped components could not print them.
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

#include "dxc/DxilContainer/DxilPipelineStateValidation.h"

#include "d3d12shader.h"

namespace {

// DxilContainer.h's four-character codes, spelled out so this file needs only
// dxcapi.h plus the standalone PSV header.
const UINT32 kFourCC_DXIL = DXC_FOURCC('D', 'X', 'I', 'L');
const UINT32 kFourCC_PSV0 = DXC_FOURCC('P', 'S', 'V', '0');

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
// directory layout to everyone. triage.py redacts the lines IT writes; the
// transcript below is our stdout and passes through untouched, so the
// redaction has to happen here.
//
// The roots are derived from this executable's own location rather than from
// the environment, so the rule holds however the harness is invoked:
//   <triage>/data/issues/4619/bin/refl4619.exe
//    5 pops up is <triage>, 3 more is <repo>.
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
  std::string triage = up(self, 5); // strip refl4619.exe/bin/4619/issues/data
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
  printf("refl4619: WALK-INCOMPLETE: %s\n", why);
  return 2;
}

int Incomplete(const char *why, HRESULT hr) {
  printf("refl4619: WALK-INCOMPLETE: %s (hr=0x%08lX %s)\n", why,
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

const char *ShaderKindName(unsigned k) {
  // D3D12_SHVER_GET_TYPE order == hlsl::DXIL::ShaderKind order.
  static const char *kNames[] = {
      "Pixel",     "Vertex",    "Geometry",     "Hull",     "Domain",
      "Compute",   "Library",   "RayGeneration", "Intersection", "AnyHit",
      "ClosestHit", "Miss",     "Callable",     "Mesh",     "Amplification",
      "Node"};
  return k < (sizeof(kNames) / sizeof(kNames[0])) ? kNames[k] : "(unknown)";
}

const char *TopologyName(unsigned t) {
  // D3D_PRIMITIVE_TOPOLOGY, only the values DXC can produce here.
  switch (t) {
  case 0:
    return "D3D_PRIMITIVE_TOPOLOGY_UNDEFINED";
  case 1:
    return "POINTLIST";
  case 2:
    return "LINELIST";
  case 3:
    return "LINESTRIP";
  case 4:
    return "TRIANGLELIST";
  case 5:
    return "TRIANGLESTRIP";
  default:
    return "(other)";
  }
}

const char *MeshTopologyName(unsigned t) {
  // hlsl::DXIL::MeshOutputTopology (include/dxc/DXIL/DxilConstants.h).
  switch (t) {
  case 0:
    return "Undefined";
  case 1:
    return "Line";
  case 2:
    return "Triangle";
  default:
    return "(other)";
  }
}

const char *PsvShaderKindName(unsigned k) {
  // PSVShaderKind (include/dxc/DxilContainer/DxilPipelineStateValidation.h).
  static const char *kNames[] = {
      "Pixel",      "Vertex",       "Geometry", "Hull",
      "Domain",     "Compute",      "Library",  "RayGeneration",
      "Intersection", "AnyHit",     "ClosestHit", "Miss",
      "Callable",   "Mesh",         "Amplification", "Node"};
  return k < (sizeof(kNames) / sizeof(kNames[0])) ? kNames[k] : "(unknown)";
}

} // namespace

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--version") || !strcmp(argv[i], "-version")) {
      // `triage.py compiler` records this, and it must identify the DLL under
      // test, not the harness -- the harness is inert plumbing.
      const char *dll = getenv("DXC_REFLECT_DLL");
      printf("refl4619 harness for issue 4619; DXC_REFLECT_DLL=%s\n",
             dll ? Redact(dll).c_str() : "(unset)");
      return 0;
    }
  }

  const char *dllEnv = getenv("DXC_REFLECT_DLL");
  if (!dllEnv || !*dllEnv) {
    fprintf(stderr, "refl4619: set DXC_REFLECT_DLL to a dxcompiler.dll\n");
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
      // flags take separate values and treating one as the filename silently
      // compiles nothing while looking like an ordinary argument error.
      source = a;
    else
      extra.push_back(Widen(argv[i]));
  }
  if (source.empty() || profile.empty()) {
    fprintf(stderr, "refl4619: usage: refl4619 -T <profile> [-E <entry>] "
                    "<source.hlsl>\n");
    return 3;
  }
  if (entry.empty())
    entry = L"main";

  printf("# refl4619: #4619 mesh-shader reflection probe\n");
  printf("dll: %s\n", Redact(dllEnv).c_str());
  printf("source: %s\n", source.c_str());
  {
    std::string p;
    for (wchar_t c : profile)
      p += (char)c;
    printf("profile: %s\n", p.c_str());
  }

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
    return Incomplete("the shader did not compile; see diagnostics above");

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
    return Incomplete("could not load the container for reflection");

  UINT32 idx = 0;
  hr = cr->FindFirstPartKind(kFourCC_DXIL, &idx);
  PrintHr("IDxcContainerReflection::FindFirstPartKind(DXIL)", hr);
  if (FAILED(hr))
    return Incomplete("container has no DXIL part");

  ID3D12ShaderReflection *refl = nullptr;
  hr = cr->GetPartReflection(idx, __uuidof(ID3D12ShaderReflection),
                             (void **)&refl);
  PrintHr("IDxcContainerReflection::GetPartReflection(ID3D12ShaderReflection)",
          hr);
  if (FAILED(hr) || !refl)
    return Incomplete("this DXIL part does not expose ID3D12ShaderReflection");

  // ---------------------------------------------------------------------
  // (B) the whole topology-bearing surface of D3D12_SHADER_DESC
  // ---------------------------------------------------------------------
  D3D12_SHADER_DESC sd = {};
  HRESULT hrDesc = refl->GetDesc(&sd);
  PrintHr("ID3D12ShaderReflection::GetDesc", hrDesc);
  if (FAILED(hrDesc))
    return Incomplete("ID3D12ShaderReflection::GetDesc failed", hrDesc);

  unsigned kind = D3D12_SHVER_GET_TYPE(sd.Version);
  printf("  D3D12_SHADER_DESC.Version=0x%08X kind=%s %u.%u\n", sd.Version,
         ShaderKindName(kind), D3D12_SHVER_GET_MAJOR(sd.Version),
         D3D12_SHVER_GET_MINOR(sd.Version));
  printf("  D3D12_SHADER_DESC.Creator=\"%s\"\n",
         sd.Creator ? sd.Creator : "(null)");
  printf("  D3D12_SHADER_DESC.InputParameters=%u OutputParameters=%u "
         "PatchConstantParameters=%u\n",
         sd.InputParameters, sd.OutputParameters, sd.PatchConstantParameters);
  printf("  D3D12_SHADER_DESC.GSOutputTopology=%u (%s)\n",
         (unsigned)sd.GSOutputTopology, TopologyName(sd.GSOutputTopology));
  printf("  D3D12_SHADER_DESC.GSMaxOutputVertexCount=%u\n",
         sd.GSMaxOutputVertexCount);
  printf("  D3D12_SHADER_DESC.InputPrimitive=%u\n", (unsigned)sd.InputPrimitive);
  printf("  D3D12_SHADER_DESC.cGSInstanceCount=%u\n", sd.cGSInstanceCount);
  printf("  D3D12_SHADER_DESC.cControlPoints=%u\n", sd.cControlPoints);
  printf("  D3D12_SHADER_DESC.HSOutputPrimitive=%u\n",
         (unsigned)sd.HSOutputPrimitive);
  printf("  D3D12_SHADER_DESC.HSPartitioning=%u\n", (unsigned)sd.HSPartitioning);
  printf("  D3D12_SHADER_DESC.TessellatorDomain=%u\n",
         (unsigned)sd.TessellatorDomain);

  D3D_PRIMITIVE gsIn = refl->GetGSInputPrimitive();
  printf("ID3D12ShaderReflection::GetGSInputPrimitive -> %u\n",
         (unsigned)gsIn);

  // ---------------------------------------------------------------------
  // (A) the reported call, verbatim from the issue body
  // ---------------------------------------------------------------------
  UINT tgx = 0xDEAD, tgy = 0xDEAD, tgz = 0xDEAD;
  UINT tgTotal = refl->GetThreadGroupSize(&tgx, &tgy, &tgz);
  printf("ID3D12ShaderReflection::GetThreadGroupSize -> returns %u\n", tgTotal);
  printf("  out x=%u y=%u z=%u\n", tgx, tgy, tgz);

  // ---------------------------------------------------------------------
  // The same facts read straight out of the container, bypassing
  // ID3D12ShaderReflection. This is what separates "the API does not expose
  // it" from "the compiler never recorded it", and it is also the reader
  // self-test for everything above.
  // ---------------------------------------------------------------------
  printf("--- container, read WITHOUT ID3D12ShaderReflection ---\n");

  unsigned psvTopology = 0xFFFFFFFF;
  unsigned psvNumThreads[3] = {0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF};
  bool psvOk = false;
  UINT32 psvIdx = 0;
  HRESULT hrPsv = cr->FindFirstPartKind(kFourCC_PSV0, &psvIdx);
  printf("PSV0 part: %s\n", SUCCEEDED(hrPsv) ? "found" : "NOT PRESENT");
  if (SUCCEEDED(hrPsv)) {
    IDxcBlob *psvBlob = nullptr;
    if (SUCCEEDED(cr->GetPartContent(psvIdx, &psvBlob)) && psvBlob) {
      DxilPipelineStateValidation psv;
      if (psv.InitFromPSV0(psvBlob->GetBufferPointer(),
                           (uint32_t)psvBlob->GetBufferSize())) {
        psvOk = true;
        PSVRuntimeInfo0 *i0 = psv.GetPSVRuntimeInfo0();
        PSVRuntimeInfo1 *i1 = psv.GetPSVRuntimeInfo1();
        PSVRuntimeInfo2 *i2 = psv.GetPSVRuntimeInfo2();
        printf("PSV.RuntimeInfoVersion=%u\n",
               i2 ? 2u : (i1 ? 1u : (i0 ? 0u : 99u)));
        if (i1) {
          printf("PSV.RuntimeInfo1.ShaderStage=%u (%s)\n",
                 (unsigned)i1->ShaderStage,
                 PsvShaderKindName(i1->ShaderStage));
          if (i1->ShaderStage == (uint8_t)PSVShaderKind::Mesh) {
            psvTopology = i1->MS1.MeshOutputTopology;
            printf("PSV.RuntimeInfo1.MS1.MeshOutputTopology=%u (%s)\n",
                   psvTopology, MeshTopologyName(psvTopology));
            printf("PSV.RuntimeInfo1.MS1.SigPrimVectors=%u\n",
                   (unsigned)i1->MS1.SigPrimVectors);
          }
        }
        if (i0 && i1 && i1->ShaderStage == (uint8_t)PSVShaderKind::Mesh) {
          printf("PSV.RuntimeInfo0.MS.MaxOutputVertices=%u "
                 "MaxOutputPrimitives=%u PayloadSizeInBytes=%u\n",
                 (unsigned)i0->MS.MaxOutputVertices,
                 (unsigned)i0->MS.MaxOutputPrimitives,
                 i0->MS.PayloadSizeInBytes);
        }
        if (i2) {
          psvNumThreads[0] = i2->NumThreadsX;
          psvNumThreads[1] = i2->NumThreadsY;
          psvNumThreads[2] = i2->NumThreadsZ;
          printf("PSV.RuntimeInfo2.NumThreads=%u,%u,%u\n", psvNumThreads[0],
                 psvNumThreads[1], psvNumThreads[2]);
        } else {
          printf("PSV.RuntimeInfo2.NumThreads=(this release's PSV predates "
                 "RuntimeInfo2)\n");
        }
      } else {
        printf("PSV0: InitFromPSV0 refused the part\n");
      }
      psvBlob->Release();
    }
  }

  // The DXIL metadata is the third, independent witness, and the only one
  // available on releases whose PSV predates RuntimeInfo2. Anchor on the
  // metadata tuple rather than on the `; NumThreads=` comment, because
  // disassembly comments are an instrument that changes across releases
  // (SKILL.md, "IR/disassembly text is no more portable than diagnostics").
  bool mdTuple = false;
  std::string numThreadsComment = "absent";
  IDxcBlobEncoding *disasm = nullptr;
  if (SUCCEEDED(comp->Disassemble(container, &disasm)) && disasm &&
      disasm->GetBufferSize()) {
    std::string text((const char *)disasm->GetBufferPointer(),
                     disasm->GetBufferSize());
    char needle[64];
    sprintf_s(needle, "!{i32 %u, i32 %u, i32 %u}", 32u, 2u, 1u);
    mdTuple = text.find(needle) != std::string::npos;
    size_t at = text.find("; NumThreads=");
    if (at != std::string::npos) {
      size_t eol = text.find('\n', at);
      numThreadsComment = text.substr(at, (eol == std::string::npos ? text.size()
                                                                    : eol) -
                                              at);
      while (!numThreadsComment.empty() &&
             (numThreadsComment.back() == '\r' || numThreadsComment.back() == ' '))
        numThreadsComment.pop_back();
    }
    disasm->Release();
  } else {
    printf("refl4619: PARSE-WARNING: could not disassemble the container; the "
           "DXIL-metadata witness is unavailable in this run\n");
  }
  printf("DXIL.numthreads-metadata-tuple{32,2,1}=%s\n",
         mdTuple ? "present" : "absent");
  printf("DXIL.disasm-comment: %s\n", numThreadsComment.c_str());

  // ---------------------------------------------------------------------
  // Self-checks, then one machine-readable RESULT line.
  // ---------------------------------------------------------------------
  printf("SELFCHECK: walk-completed=yes\n");
  printf("SELFCHECK: shader-kind=%s\n", ShaderKindName(kind));
  printf("SELFCHECK: psv-readable=%s\n", psvOk ? "yes" : "no");
  if (!psvOk)
    printf("refl4619: PARSE-WARNING: PSV0 was not readable, so the "
           "container-side witnesses below are missing rather than absent\n");

  printf("RESULT: GETTHREADGROUPSIZE=%u,%u,%u GETTHREADGROUPSIZE-RETURN=%u "
         "SHADERDESC-TOPOLOGY-FIELDS=GSOutputTopology:%u,InputPrimitive:%u,"
         "HSOutputPrimitive:%u,TessellatorDomain:%u,GSInputPrimitive:%u "
         "PSV-MESH-TOPOLOGY=%u PSV-NUMTHREADS=%u,%u,%u\n",
         tgx, tgy, tgz, tgTotal, (unsigned)sd.GSOutputTopology,
         (unsigned)sd.InputPrimitive, (unsigned)sd.HSOutputPrimitive,
         (unsigned)sd.TessellatorDomain, (unsigned)gsIn, psvTopology,
         psvNumThreads[0], psvNumThreads[1], psvNumThreads[2]);
  return 0;
}
