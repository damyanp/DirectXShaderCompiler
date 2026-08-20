// pdb5721-harness.cpp -- #5721
//
// Reproduces the reported symptom directly through the COM API, since it is
// not observable from any `dxc`/`dxl` command line at all (see expected.md):
// `DxcContext::Link()` (tools/clang/tools/dxclib/dxc.cpp) never calls
// `GetOutput(DXC_OUT_PDB, ...)` on the linker's result, so no CLI flag
// combination can surface this.
//
// Steps, matching the issue's own "Steps to Reproduce" verbatim:
//   1. Compile repro.hlsl as a library (-T lib_6_3, -Zi so there is debug
//      info to carry through the link).
//   2. RegisterLibrary the compiled blob with IDxcLinker.
//   3. IDxcLinker::Link(L"main", L"cs_6_3", ..., args={-Zi,-Qstrip_debug},
//      &ppResult) where ppResult is IDxcOperationResult* per the interface.
//   4. QueryInterface ppResult for IDxcResult.
//   5. GetOutput(DXC_OUT_PDB, ...) on that IDxcResult.
//
// Two controls run alongside the primary measurement, both against the
// SAME linked result object / SAME source, so the absence in step 5 cannot
// be explained by anything other than the DXC_OUT_PDB clause specifically:
//
//   self-test (anti-vacuity): GetOutput(DXC_OUT_OBJECT, ...) on the very
//   same linked IDxcResult must succeed -- proving GetOutput/QueryInterface
//   works on this object in general, and the DXC_OUT_PDB absence is not an
//   artifact of a broken harness or a failed link.
//
//   positive control: an ordinary (non-linked) IDxcCompiler3::Compile of the
//   identical source, straight to cs_6_3, with the identical -Zi
//   -Qstrip_debug flags. If GetOutput(DXC_OUT_PDB, ...) succeeds there, the
//   defect is specific to the linker path, not to the flags or the shader.
//
// Standalone compile via cl.exe (see pdb5721-gen.py), outside build/; no
// DXC CMake target is built or touched. Statically links the registered
// ground-truth main-debug import lib (build/Debug/lib/dxcompiler.lib), so
// this measures exactly the binary triage.py registered as `main-debug`.

#include "dxc/Support/WinIncludes.h"
#include "dxc/dxcapi.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#pragma comment(lib, "dxcompiler.lib")

static const char *hrName(HRESULT hr) {
  switch (hr) {
  case S_OK:
    return "S_OK";
  case E_INVALIDARG:
    return "E_INVALIDARG";
  case E_NOINTERFACE:
    return "E_NOINTERFACE";
  case E_FAIL:
    return "E_FAIL";
  case E_NOTIMPL:
    return "E_NOTIMPL";
  default:
    return "?";
  }
}

static void printHr(const char *label, HRESULT hr) {
  printf("%s = 0x%08X (%s)\n", label, (unsigned)hr, hrName(hr));
}

static std::string readFile(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) {
    printf("FATAL: could not open %s\n", path);
    exit(2);
  }
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::string data;
  data.resize((size_t)size);
  fread(&data[0], 1, (size_t)size, f);
  fclose(f);
  return data;
}

int main(int argc, char **argv) {
  const char *srcPath = argc > 1 ? argv[1] : "repro.hlsl";
  std::string source = readFile(srcPath);
  printf("source: %s (%zu bytes)\n\n", srcPath, source.size());

  IDxcCompiler3 *pCompiler = nullptr;
  HRESULT hr =
      DxcCreateInstance(CLSID_DxcCompiler, IID_PPV_ARGS(&pCompiler));
  printHr("DxcCreateInstance(CLSID_DxcCompiler)", hr);
  if (FAILED(hr))
    return 1;

  DxcBuffer srcBuf{source.data(), source.size(), DXC_CP_UTF8};

  // --- Stage 1: compile the library (needs -Zi so it carries debug info to
  //     link; the issue's own repro passes -Zi/-Qstrip_debug to Link, not to
  //     the library compile, but Link only has debug info to serialize if
  //     the library it links has some -- see dxclinker.cpp's
  //     "Always save debug info. If lib has debug info, the link result
  //     will have debug info.")
  std::vector<LPCWSTR> libArgs = {L"-T", L"lib_6_3", L"-Zi"};
  IDxcResult *pLibResult = nullptr;
  hr = pCompiler->Compile(&srcBuf, libArgs.data(), (UINT32)libArgs.size(),
                          nullptr, IID_PPV_ARGS(&pLibResult));
  printHr("\nCompile(lib_6_3 -Zi)", hr);
  HRESULT libStatus = E_FAIL;
  if (pLibResult)
    pLibResult->GetStatus(&libStatus);
  printHr("  lib compile status", libStatus);
  if (FAILED(hr) || FAILED(libStatus)) {
    IDxcBlobUtf8 *pErr = nullptr;
    if (pLibResult)
      pLibResult->GetOutput(DXC_OUT_ERRORS, IID_PPV_ARGS(&pErr), nullptr);
    if (pErr && pErr->GetStringLength())
      printf("  lib compile errors:\n%s\n", pErr->GetStringPointer());
    return 1;
  }
  IDxcBlob *pLibBlob = nullptr;
  pLibResult->GetOutput(DXC_OUT_OBJECT, IID_PPV_ARGS(&pLibBlob), nullptr);
  printf("  lib object size: %zu bytes\n", pLibBlob->GetBufferSize());

  // --- Stage 2: link, exactly per the issue's steps to reproduce.
  IDxcLinker *pLinker = nullptr;
  hr = DxcCreateInstance(CLSID_DxcLinker, IID_PPV_ARGS(&pLinker));
  printHr("\nDxcCreateInstance(CLSID_DxcLinker)", hr);
  if (FAILED(hr))
    return 1;

  hr = pLinker->RegisterLibrary(L"lib5721", pLibBlob);
  printHr("RegisterLibrary(lib5721)", hr);

  std::vector<LPCWSTR> linkArgs = {L"-Zi", L"-Qstrip_debug"};
  LPCWSTR libNames[1] = {L"lib5721"};
  IDxcOperationResult *pLinkOpResult = nullptr;
  hr = pLinker->Link(L"main", L"cs_6_3", libNames, 1, linkArgs.data(),
                     (UINT32)linkArgs.size(), &pLinkOpResult);
  printHr("Link(\"main\", \"cs_6_3\", args={-Zi,-Qstrip_debug})", hr);

  HRESULT linkStatus = E_FAIL;
  if (pLinkOpResult)
    pLinkOpResult->GetStatus(&linkStatus);
  printHr("  link status", linkStatus);
  if (FAILED(hr) || FAILED(linkStatus)) {
    IDxcBlobEncoding *pErr = nullptr;
    if (pLinkOpResult)
      pLinkOpResult->GetErrorBuffer(&pErr);
    if (pErr)
      printf("  link errors:\n%s\n",
             (const char *)pErr->GetBufferPointer());
    return 1;
  }

  // --- Step 4: QueryInterface for IDxcResult, per the issue.
  IDxcResult *pLinkResult = nullptr;
  hr = pLinkOpResult->QueryInterface(IID_PPV_ARGS(&pLinkResult));
  printHr("\nQueryInterface(link result, IID_IDxcResult)", hr);
  if (FAILED(hr)) {
    printf("Cannot proceed: linker result does not support IDxcResult at "
           "all.\n");
    return 1;
  }

  // --- Step 5 (the reported symptom).
  BOOL hasPdb = pLinkResult->HasOutput(DXC_OUT_PDB);
  printf("HasOutput(DXC_OUT_PDB) on linked result = %s\n",
         hasPdb ? "TRUE" : "FALSE");
  IDxcBlob *pPdbBlob = nullptr;
  IDxcBlobWide *pPdbName = nullptr;
  HRESULT pdbHr = pLinkResult->GetOutput(
      DXC_OUT_PDB, IID_PPV_ARGS(&pPdbBlob), &pPdbName);
  printHr("GetOutput(DXC_OUT_PDB) on linked result", pdbHr);
  if (SUCCEEDED(pdbHr) && pPdbBlob)
    printf("  linked PDB blob size: %zu bytes\n", pPdbBlob->GetBufferSize());
  if (pPdbName)
    printf("  linked PDB name: %ls\n", pPdbName->GetStringPointer());

  // --- Self-test / anti-vacuity control: same result object, a DXC_OUT_KIND
  //     that DxcLinker::Link *does* populate (DXC_OUT_OBJECT). Must succeed,
  //     or the absence above proves nothing about GetOutput/QueryInterface
  //     working at all on this object.
  IDxcBlob *pLinkedObj = nullptr;
  HRESULT objHr = pLinkResult->GetOutput(DXC_OUT_OBJECT,
                                         IID_PPV_ARGS(&pLinkedObj), nullptr);
  printHr("\nSELF-TEST GetOutput(DXC_OUT_OBJECT) on linked result", objHr);
  if (SUCCEEDED(objHr) && pLinkedObj)
    printf("  linked object size: %zu bytes (self-test proves GetOutput "
           "works on this result object)\n",
           pLinkedObj->GetBufferSize());

  // --- Positive control: ordinary (non-linked) compile of the SAME source,
  //     SAME target profile, SAME flags. Isolates the linker path as the
  //     one at fault.
  std::vector<LPCWSTR> directArgs = {L"-T",           L"cs_6_3", L"-E",
                                     L"main",         L"-Zi",    L"-Qstrip_debug"};
  IDxcResult *pDirectResult = nullptr;
  hr = pCompiler->Compile(&srcBuf, directArgs.data(),
                          (UINT32)directArgs.size(), nullptr,
                          IID_PPV_ARGS(&pDirectResult));
  printHr("\nCONTROL Compile(cs_6_3 -Zi -Qstrip_debug, no linker)", hr);
  HRESULT directStatus = E_FAIL;
  if (pDirectResult)
    pDirectResult->GetStatus(&directStatus);
  printHr("  direct compile status", directStatus);
  if (SUCCEEDED(hr) && SUCCEEDED(directStatus)) {
    BOOL directHasPdb = pDirectResult->HasOutput(DXC_OUT_PDB);
    printf("  CONTROL HasOutput(DXC_OUT_PDB) on direct compile = %s\n",
           directHasPdb ? "TRUE" : "FALSE");
    IDxcBlob *pDirectPdb = nullptr;
    HRESULT directPdbHr = pDirectResult->GetOutput(
        DXC_OUT_PDB, IID_PPV_ARGS(&pDirectPdb), nullptr);
    printHr("  CONTROL GetOutput(DXC_OUT_PDB) on direct compile",
            directPdbHr);
    if (SUCCEEDED(directPdbHr) && pDirectPdb)
      printf("  direct PDB blob size: %zu bytes\n",
             pDirectPdb->GetBufferSize());
  }

  printf("\nSUMMARY: linked HasOutput(DXC_OUT_PDB)=%s  "
         "linked GetOutput(DXC_OUT_PDB) hr=0x%08X  "
         "self-test GetOutput(DXC_OUT_OBJECT) hr=0x%08X\n",
         hasPdb ? "TRUE" : "FALSE", (unsigned)pdbHr, (unsigned)objHr);

  return 0;
}
