// isense_probe.cpp
//
// Standalone evidence-gathering harness for DXC issue #5173
// ("IDxcCursor misses semantics"). This is NOT part of the DXC build: it is
// a throwaway tool that dynamically loads a given dxcompiler.dll (ground
// truth or any cataloged release) via dxcapi.use.h's SpecificDllLoader, then
// drives the public IDxcIntelliSense / IDxcIndex / IDxcTranslationUnit /
// IDxcCursor COM interfaces to parse a shader and dump the cursor tree:
// kind, spelling, and display name for every node, recursively.
//
// Usage: isense_probe.exe <path-to-dxcompiler.dll> <path-to-source.hlsl>
//
// No DXC source is modified or rebuilt: this links against nothing but the
// public headers (dxcapi.h, dxcisense.h, dxcapi.use.h are all header-only
// for the pieces used here) and loads the target DLL purely at runtime.

#include <cstdio>
#include <string>
#include <vector>
#include <windows.h>

#include "dxc/Support/dxcapi.use.h"
#include "dxc/dxcapi.h"
#include "dxc/dxcisense.h"

using namespace dxc;

static const char *KindName(DxcCursorKind k) {
  switch (k) {
  case DxcCursor_UnexposedDecl:
    return "UnexposedDecl";
  case DxcCursor_StructDecl:
    return "StructDecl";
  case DxcCursor_FieldDecl:
    return "FieldDecl";
  case DxcCursor_FunctionDecl:
    return "FunctionDecl";
  case DxcCursor_ParmDecl:
    return "ParmDecl";
  case DxcCursor_TypeRef:
    return "TypeRef";
  case DxcCursor_UnexposedAttr:
    return "UnexposedAttr";
  case DxcCursor_AnnotateAttr:
    return "AnnotateAttr";
  case DxcCursor_AsmLabelAttr:
    return "AsmLabelAttr";
  case DxcCursor_PackedAttr:
    return "PackedAttr";
  case DxcCursor_TranslationUnit:
    return "TranslationUnit";
  case DxcCursor_CompoundStmt:
    return "CompoundStmt";
  case DxcCursor_ReturnStmt:
    return "ReturnStmt";
  default:
    return "(other)";
  }
}

static bool IsAttrKind(DxcCursorKind k) {
  return k >= DxcCursor_FirstAttr && k <= DxcCursor_LastAttr;
}

static void PrintIndent(int depth) {
  for (int i = 0; i < depth; i++)
    fputs("  ", stdout);
}

static void Walk(IDxcCursor *cursor, int depth) {
  DxcCursorKind kind = (DxcCursorKind)0;
  cursor->GetKind(&kind);

  LPSTR spelling = nullptr;
  cursor->GetSpelling(&spelling);

  BSTR display = nullptr;
  cursor->GetDisplayName(&display);

  PrintIndent(depth);
  printf("kind=%d(%s)%s spelling=\"%s\" display=\"%ls\"\n", (int)kind,
        KindName(kind), IsAttrKind(kind) ? " [ATTR]" : "",
        spelling ? spelling : "", display ? display : L"");

  if (spelling)
    CoTaskMemFree(spelling);
  if (display)
    SysFreeString(display);

  unsigned count = 0;
  IDxcCursor **children = nullptr;
  HRESULT hr = cursor->GetChildren(0, 256, &count, &children);
  if (SUCCEEDED(hr) && children != nullptr) {
    for (unsigned i = 0; i < count; i++) {
      Walk(children[i], depth + 1);
      children[i]->Release();
    }
    CoTaskMemFree(children);
  }
}

static std::string ReadFile(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) {
    fprintf(stderr, "FATAL: could not open %s\n", path);
    exit(3);
  }
  fseek(f, 0, SEEK_END);
  long len = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::string contents(len, '\0');
  fread(&contents[0], 1, len, f);
  fclose(f);
  return contents;
}

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr,
            "usage: isense_probe <path-to-dxcompiler.dll> <source.hlsl>\n");
    return 2;
  }
  const char *dllPath = argv[1];
  const char *srcPath = argv[2];

  printf("# harness: isense_probe\n");
  printf("# dxcompiler: %s\n", dllPath);
  printf("# source: %s\n", srcPath);

  SpecificDllLoader loader;
  HRESULT hr = loader.InitializeForDll(dllPath, "DxcCreateInstance");
  if (FAILED(hr)) {
    printf("# exit: InitializeForDll failed hr=0x%08X\n", (unsigned)hr);
    return 1;
  }

  IDxcIntelliSense *isense = nullptr;
  hr = loader.CreateInstance(CLSID_DxcIntelliSense, &isense);
  if (FAILED(hr)) {
    printf("# exit: CreateInstance(CLSID_DxcIntelliSense) failed hr=0x%08X\n",
          (unsigned)hr);
    return 1;
  }

  IDxcIndex *index = nullptr;
  hr = isense->CreateIndex(&index);
  if (FAILED(hr)) {
    printf("# exit: CreateIndex failed hr=0x%08X\n", (unsigned)hr);
    isense->Release();
    return 1;
  }

  std::string src = ReadFile(srcPath);

  IDxcUnsavedFile *unsaved = nullptr;
  hr = isense->CreateUnsavedFile("source.hlsl", src.c_str(),
                                 (unsigned)src.size(), &unsaved);
  if (FAILED(hr)) {
    printf("# exit: CreateUnsavedFile failed hr=0x%08X\n", (unsigned)hr);
    index->Release();
    isense->Release();
    return 1;
  }

  IDxcTranslationUnit *tu = nullptr;
  hr = index->ParseTranslationUnit("source.hlsl", nullptr, 0, &unsaved, 1,
                                   DxcTranslationUnitFlags_UseCallerThread,
                                   &tu);
  if (FAILED(hr)) {
    printf("# exit: ParseTranslationUnit failed hr=0x%08X\n", (unsigned)hr);
    unsaved->Release();
    index->Release();
    isense->Release();
    return 1;
  }

  unsigned diagCount = 0;
  tu->GetNumDiagnostics(&diagCount);
  printf("# diagnostics: %u\n", diagCount);
  for (unsigned i = 0; i < diagCount; i++) {
    IDxcDiagnostic *diag = nullptr;
    if (SUCCEEDED(tu->GetDiagnostic(i, &diag)) && diag != nullptr) {
      LPSTR text = nullptr;
      diag->FormatDiagnostic(DxcDiagnostic_DisplaySourceLocation, &text);
      printf("#   diag[%u]: %s\n", i, text ? text : "(null)");
      if (text)
        CoTaskMemFree(text);
      diag->Release();
    }
  }

  IDxcCursor *root = nullptr;
  hr = tu->GetCursor(&root);
  if (FAILED(hr)) {
    printf("# exit: GetCursor failed hr=0x%08X\n", (unsigned)hr);
  } else {
    printf("# cursor tree:\n");
    Walk(root, 0);
    root->Release();
  }

  tu->Release();
  unsaved->Release();
  index->Release();
  isense->Release();

  printf("# exit: 0\n");
  return 0;
}
