// fc2604 -- #2604 "Handle -Fc in Compile API in order to support separate
// simultaneous disassembly output."
//
// dxc.exe cannot answer this issue. -Fc is declared `Flags<[DriverOption]>`
// (include/dxc/Support/HLSLOptions.td), and dxc.exe parses with
// `DxcFlags = CoreOption | DriverOption` while the library parses with
// `CompilerFlags = CoreOption` alone (include/dxc/Support/HLSLOptions.h) --
// so the command line and the compile API take *different* code paths through
// the same option table, and that difference is the entire subject of the
// issue. Probing dxc.exe would measure the path that already works.
//
// This harness is therefore registered as a compiler (SKILL.md, "When the
// symptom is in a pass dxc.exe cannot run, register the harness as a
// compiler"), so `triage.py run`, --shader/--args controls, --expect and
// `reindex` all keep working on it. The compile implementation under test
// comes from DXC_FC_DLL, so the same harness can be pointed at any release's
// dxcompiler.dll -- the device #2922/#2923/#3237 used.
//
// Seven cases, chosen so that the anchors work on every release and the
// symptom clauses are positive strings rather than absences:
//
//   c1-fc            IDxcCompiler::Compile, extra args `-Fc <file>`
//   c1-fc-qunused    ... plus -Qunused-arguments, which is a CoreOption and
//                    so IS visible to the library; it suppresses the unknown
//                    argument check in ReadDxcOpts, which separates
//                    "rejected" from "accepted and ignored"
//   c1-baseline      ... with -Fc removed.  ANCHOR: the compile works
//   c1-disassemble   IDxcCompiler::Disassemble on c1-baseline's object.
//                    ANCHOR: this DLL *can* disassemble; the listing is
//                    reachable, just not from Compile
//   c3-fc            IDxcCompiler3::Compile, full argv incl. `-Fc <file>`
//   c3-fc-qunused    ... plus -Qunused-arguments
//   c3-baseline      ... with -Fc removed
//
// The c1-* cases use the interface that existed when the issue was filed in
// 2019; IDxcCompiler3 arrived in DXC 1.6 and is reported `unavailable` on
// older DLLs rather than aborting the probe, so the legacy rows still carry
// the full history.
//
// Every case reports the same four observables:
//   call     the HRESULT the Compile/Disassemble call itself returned
//   status   IDxcOperationResult::GetStatus -- where E_INVALIDARG shows up
//   object   whether an object blob came back
//   disasm   whether IDxcResult carries DXC_OUT_DISASSEMBLY
//   fcfile   whether the file named by -Fc exists after the call
//
// `fcfile` is deleted before each case. The same arguments are a valid
// dxc.exe command line, dxc.exe *does* write that file, and a leftover from
// such a run would otherwise read as "the API wrote it".
//
// SELF-CONSISTENCY (SKILL.md, "A control cannot catch a broken reader",
// measured on #2923): the RESULT lines are never printed unless every case
// that could run did run. Anything earlier prints a loud
// `fc2604: PROBE-INCOMPLETE:` marker and exits 2.
//
// The HRESULTs here are API return values and are deliberately NOT folded
// into the process exit code: dxc.exe returns E_FAIL for ordinary diagnosed
// errors and the two must not be conflated. Exit 0 means "the probe
// completed", not "no bug".
//
//   set DXC_FC_DLL=<...>\dxcompiler.dll
//   fc2604.exe -T ps_6_0 -E main -Fc repro-fc.asm repro.hlsl

#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "dxc/dxcapi.h"

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

// Rewrite an absolute path to the placeholders triage.py uses in its own
// capture headers: <cache>, <triage>, <repo>, most specific first, forward
// slashes. This output is committed, so a raw path would ship one machine's
// directory layout to everyone. triage.py redacts the lines IT writes; the
// transcript below is our stdout and passes through untouched, so the
// redaction has to happen here too.
//
// The roots are derived from this executable's own location rather than from
// the environment, so the rule holds however the harness is invoked:
//   <triage>/data/issues/2604/bin/fc2604.exe
//    -- <triage> is 5 pops up, <repo> 3 more.
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
  std::string triage = up(self, 5); // strip fc2604.exe/bin/2604/issues/data
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
  printf("fc2604: PROBE-INCOMPLETE: %s\n", why);
  return 2;
}

int Incomplete(const char *why, HRESULT hr) {
  printf("fc2604: PROBE-INCOMPLETE: %s (hr=0x%08lX %s)\n", why,
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

// Collapse a diagnostic to one line so the transcript stays readable. The
// full text is what the compiler returned; only the line breaks change, and
// the marker says so.
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

bool FileExists(const std::string &path) {
  return GetFileAttributesA(path.c_str()) != INVALID_FILE_ATTRIBUTES;
}

struct Observation {
  const char *name = "";
  bool ran = false;
  HRESULT call = E_FAIL;
  HRESULT status = E_FAIL;
  bool haveStatus = false;
  const char *object = "n/a";
  const char *disasm = "n/a";
  const char *fcfile = "n/a";
  std::string errors;
  std::string outputs;
  std::string skipped;
};

void PrintDetail(const Observation &o, const char *what,
                 const std::string &fcPath) {
  printf("\n[%s] %s\n", o.name, what);
  if (!o.ran) {
    printf("  skipped                    %s\n", o.skipped.c_str());
    return;
  }
  printf("  call returned              0x%08lX (%s)\n", (unsigned long)o.call,
         HrName(o.call));
  if (o.haveStatus)
    printf("  result status              0x%08lX (%s)\n",
           (unsigned long)o.status, HrName(o.status));
  if (!o.errors.empty())
    printf("  errors                     \"%s\"\n", o.errors.c_str());
  if (!o.outputs.empty())
    printf("  IDxcResult outputs         %s\n", o.outputs.c_str());
  printf("  object blob                %s\n", o.object);
  printf("  DXC_OUT_DISASSEMBLY        %s\n", o.disasm);
  if (strcmp(o.fcfile, "n/a") != 0)
    printf("  file \"%s\"        %s\n", fcPath.c_str(),
           strcmp(o.fcfile, "present") == 0 ? "created" : "NOT created");
}

const char *KindName(DXC_OUT_KIND k) {
  switch (k) {
  case DXC_OUT_NONE:
    return "NONE";
  case DXC_OUT_OBJECT:
    return "OBJECT";
  case DXC_OUT_ERRORS:
    return "ERRORS";
  case DXC_OUT_PDB:
    return "PDB";
  case DXC_OUT_SHADER_HASH:
    return "SHADER_HASH";
  case DXC_OUT_DISASSEMBLY:
    return "DISASSEMBLY";
  case DXC_OUT_HLSL:
    return "HLSL";
  case DXC_OUT_TEXT:
    return "TEXT";
  case DXC_OUT_REFLECTION:
    return "REFLECTION";
  case DXC_OUT_ROOT_SIGNATURE:
    return "ROOT_SIGNATURE";
  case DXC_OUT_EXTRA_OUTPUTS:
    return "EXTRA_OUTPUTS";
  default:
    return "(other)";
  }
}

// Enumerate what the result actually carries. This is the observation the
// issue body is really about: "separate simultaneous disassembly output"
// means DXC_OUT_DISASSEMBLY appearing here alongside DXC_OUT_OBJECT.
void ReadOutputs(IUnknown *resultUnk, Observation &o) {
  IDxcResult *r = nullptr;
  if (FAILED(resultUnk->QueryInterface(__uuidof(IDxcResult), (void **)&r)) ||
      !r) {
    // Pre-1.6 dxcompiler.dll has no IDxcResult, so there is no output-kind
    // channel at all: IDxcOperationResult exposes exactly GetStatus,
    // GetResult and GetErrorBuffer, and none of them can carry a listing.
    // `absent` is therefore the honest reading of what the CALLER received,
    // which is what the issue is about -- and it keeps one predicate valid
    // across the whole release history instead of silently scoring every
    // pre-1.6 release no-repro on a token difference. The distinction
    // between "no such concept" and "concept present but empty" is not lost:
    // it is printed on the next line.
    o.outputs = "(IDxcResult unavailable on this DLL; IDxcOperationResult "
                "has no channel for a disassembly listing)";
    o.disasm = "absent";
    return;
  }
  std::string list;
  UINT32 n = r->GetNumOutputs();
  for (UINT32 i = 0; i < n; ++i) {
    if (!list.empty())
      list += " ";
    list += KindName(r->GetOutputByIndex(i));
  }
  o.outputs = list.empty() ? "(none)" : list;
  o.disasm = r->HasOutput(DXC_OUT_DISASSEMBLY) ? "present" : "absent";
  r->Release();
}

} // namespace

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--version") || !strcmp(argv[i], "-version")) {
      // `triage.py compiler` records this, and it must identify the DLL under
      // test, not the harness -- the harness is inert plumbing.
      const char *dll = getenv("DXC_FC_DLL");
      printf("fc2604 harness for issue 2604; DXC_FC_DLL=%s\n",
             dll ? Redact(dll).c_str() : "(unset)");
      return 0;
    }
  }

  const char *dllEnv = getenv("DXC_FC_DLL");
  if (!dllEnv || !*dllEnv) {
    fprintf(stderr, "fc2604: set DXC_FC_DLL to a dxcompiler.dll\n");
    return 3;
  }

  // Parse the dxc-style command line. Everything is kept verbatim for the
  // IDxcCompiler3 argv; the pieces the legacy interface takes as dedicated
  // parameters (-T, -E, source name) are also pulled out separately.
  std::string profile, entry, source, fcPath;
  std::vector<std::string> argvAll;   // exactly as filed, for IDxcCompiler3
  std::vector<std::string> argvNoFc;  // ... with the -Fc operand removed
  std::vector<std::string> extraFc;   // extras for IDxcCompiler, incl. -Fc
  std::vector<std::string> extraNoFc; // ... without

  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    bool isFc = (a == "-Fc" || a == "/Fc");
    bool isJoinedFc = (a.size() > 3 && (a[0] == '-' || a[0] == '/') &&
                       a.compare(1, 2, "Fc") == 0);
    if (isFc && i + 1 < argc) {
      fcPath = argv[i + 1];
      argvAll.push_back(a);
      argvAll.push_back(argv[i + 1]);
      extraFc.push_back(a);
      extraFc.push_back(argv[i + 1]);
      ++i;
      continue;
    }
    if (isJoinedFc) {
      fcPath = a.substr(3);
      argvAll.push_back(a);
      extraFc.push_back(a);
      continue;
    }
    argvAll.push_back(a);
    argvNoFc.push_back(a);
    if ((a == "-T" || a == "/T") && i + 1 < argc) {
      profile = argv[++i];
      argvAll.push_back(profile);
      argvNoFc.push_back(profile);
      continue;
    }
    if ((a == "-E" || a == "/E") && i + 1 < argc) {
      entry = argv[++i];
      argvAll.push_back(entry);
      argvNoFc.push_back(entry);
      continue;
    }
    // Identify the source by suffix, not by "does not start with a dash":
    // flags take separate values and treating one as the filename silently
    // compiles nothing while looking like an ordinary argument error.
    if (a.size() >= 5 && a.compare(a.size() - 5, 5, ".hlsl") == 0 &&
        a[0] != '-' && a[0] != '/') {
      source = a;
      continue;
    }
    extraFc.push_back(a);
    extraNoFc.push_back(a);
  }

  if (source.empty() || profile.empty()) {
    fprintf(stderr, "fc2604: usage: fc2604 -T <profile> [-E <entry>] "
                    "[-Fc <listing>] <source.hlsl>\n");
    return 3;
  }
  if (entry.empty())
    entry = "main";
  if (fcPath.empty())
    fcPath = "fc2604-out.asm";

  printf("# fc2604: #2604 -Fc in the compile API\n");
  printf("dll: %s\n", Redact(dllEnv).c_str());
  printf("source: %s\n", source.c_str());
  printf("argv as filed: %s\n", [&] {
    std::string s;
    for (auto &a : argvAll)
      s += (s.empty() ? "" : " ") + a;
    return s;
  }().c_str());
  printf("-Fc operand: %s\n", fcPath.c_str());

  HMODULE mod = LoadLibraryW(Widen(dllEnv).c_str());
  if (!mod)
    return Incomplete("LoadLibraryW failed on DXC_FC_DLL");
  auto createInstance =
      (DxcCreateInstanceProc)GetProcAddress(mod, "DxcCreateInstance");
  if (!createInstance)
    return Incomplete("no DxcCreateInstance export in DXC_FC_DLL");

  IDxcLibrary *lib = nullptr;
  if (FAILED(createInstance(CLSID_DxcLibrary, __uuidof(IDxcLibrary),
                            (void **)&lib)) ||
      !lib)
    return Incomplete("DxcCreateInstance(CLSID_DxcLibrary) failed");

  IDxcBlobEncoding *src = nullptr;
  if (FAILED(lib->CreateBlobFromFile(Widen(source.c_str()).c_str(), nullptr,
                                     &src)) ||
      !src)
    return Incomplete("CreateBlobFromFile failed (is the source there?)");

  IDxcCompiler *c1 = nullptr;
  if (FAILED(createInstance(CLSID_DxcCompiler, __uuidof(IDxcCompiler),
                            (void **)&c1)) ||
      !c1)
    return Incomplete("DxcCreateInstance(CLSID_DxcCompiler) failed");

  IDxcCompiler3 *c3 = nullptr;
  HRESULT c3hr = createInstance(CLSID_DxcCompiler, __uuidof(IDxcCompiler3),
                                (void **)&c3);
  printf("IDxcCompiler (legacy): available\n");
  printf("IDxcCompiler3: %s\n",
         (SUCCEEDED(c3hr) && c3) ? "available"
                                 : "unavailable (predates DXC 1.6)");

  auto widened = [](const std::vector<std::string> &in) {
    std::vector<std::wstring> out;
    for (auto &s : in)
      out.push_back(Widen(s.c_str()));
    return out;
  };

  IDxcBlob *baselineObject = nullptr;

  // --- IDxcCompiler (the interface the 2019 issue was filed against) -------
  auto runC1 = [&](const char *name, std::vector<std::string> extra,
                   bool expectFcFile, bool keepObject) {
    Observation o;
    o.name = name;
    o.ran = true;
    if (expectFcFile)
      DeleteFileA(fcPath.c_str());
    std::vector<std::wstring> w = widened(extra);
    std::vector<LPCWSTR> ptrs;
    for (auto &s : w)
      ptrs.push_back(s.c_str());

    IDxcOperationResult *res = nullptr;
    o.call = c1->Compile(src, Widen(source.c_str()).c_str(),
                         Widen(entry.c_str()).c_str(),
                         Widen(profile.c_str()).c_str(),
                         ptrs.empty() ? nullptr : ptrs.data(),
                         (UINT32)ptrs.size(), nullptr, 0, nullptr, &res);
    if (SUCCEEDED(o.call) && res) {
      o.haveStatus = SUCCEEDED(res->GetStatus(&o.status));
      IDxcBlobEncoding *errs = nullptr;
      if (SUCCEEDED(res->GetErrorBuffer(&errs)) && errs) {
        if (errs->GetBufferSize())
          o.errors = OneLine((const char *)errs->GetBufferPointer(),
                             (size_t)errs->GetBufferSize());
        errs->Release();
      }
      IDxcBlob *obj = nullptr;
      if (SUCCEEDED(res->GetResult(&obj)) && obj && obj->GetBufferSize()) {
        o.object = "present";
        if (keepObject && !baselineObject) {
          baselineObject = obj;
          baselineObject->AddRef();
        }
        obj->Release();
      } else {
        o.object = "absent";
        if (obj)
          obj->Release();
      }
      ReadOutputs(res, o);
      res->Release();
    }
    if (expectFcFile)
      o.fcfile = FileExists(fcPath) ? "present" : "absent";
    return o;
  };

  Observation c1fc = runC1("c1-fc", extraFc, true, false);
  std::vector<std::string> extraFcQ = extraFc;
  extraFcQ.push_back("-Qunused-arguments");
  Observation c1fcq = runC1("c1-fc-qunused", extraFcQ, true, false);
  Observation c1base = runC1("c1-baseline", extraNoFc, false, true);

  // --- IDxcCompiler::Disassemble -- the anchor ----------------------------
  Observation c1dis;
  c1dis.name = "c1-disassemble";
  size_t disasmBytes = 0;
  if (!baselineObject) {
    c1dis.skipped = "c1-baseline produced no object to disassemble";
  } else {
    c1dis.ran = true;
    IDxcBlobEncoding *text = nullptr;
    c1dis.call = c1->Disassemble(baselineObject, &text);
    if (SUCCEEDED(c1dis.call) && text && text->GetBufferSize()) {
      c1dis.disasm = "present";
      disasmBytes = (size_t)text->GetBufferSize();
    } else {
      c1dis.disasm = "absent";
    }
    if (text)
      text->Release();
  }

  // --- IDxcCompiler3 (the modern API, DXC 1.6+) ---------------------------
  auto runC3 = [&](const char *name, const std::vector<std::string> &args,
                   bool expectFcFile) {
    Observation o;
    o.name = name;
    if (!c3) {
      o.skipped = "IDxcCompiler3 is not available on this DLL";
      return o;
    }
    o.ran = true;
    if (expectFcFile)
      DeleteFileA(fcPath.c_str());
    std::vector<std::wstring> w = widened(args);
    std::vector<LPCWSTR> ptrs;
    for (auto &s : w)
      ptrs.push_back(s.c_str());

    DxcBuffer buf = {src->GetBufferPointer(), src->GetBufferSize(),
                     DXC_CP_UTF8};
    IDxcResult *res = nullptr;
    o.call = c3->Compile(&buf, ptrs.empty() ? nullptr : ptrs.data(),
                         (UINT32)ptrs.size(), nullptr, IID_PPV_ARGS(&res));
    if (SUCCEEDED(o.call) && res) {
      o.haveStatus = SUCCEEDED(res->GetStatus(&o.status));
      IDxcBlobEncoding *errs = nullptr;
      if (SUCCEEDED(res->GetErrorBuffer(&errs)) && errs) {
        if (errs->GetBufferSize())
          o.errors = OneLine((const char *)errs->GetBufferPointer(),
                             (size_t)errs->GetBufferSize());
        errs->Release();
      }
      o.object = res->HasOutput(DXC_OUT_OBJECT) ? "present" : "absent";
      ReadOutputs(res, o);
      res->Release();
    }
    if (expectFcFile)
      o.fcfile = FileExists(fcPath) ? "present" : "absent";
    return o;
  };

  Observation c3fc = runC3("c3-fc", argvAll, true);
  std::vector<std::string> argvAllQ = argvAll;
  argvAllQ.push_back("-Qunused-arguments");
  Observation c3fcq = runC3("c3-fc-qunused", argvAllQ, true);
  Observation c3base = runC3("c3-baseline", argvNoFc, false);

  // --- the SPIR-V path ----------------------------------------------------
  // docs/SPIR-V.rst lists `-Fc` among the options SPIR-V CodeGen supports and
  // states they "are also recognized by the library API calls". That is the
  // exact sentence the 2020 comment on this issue cites, so the claim is
  // measured here rather than argued about. If these cases behaved
  // differently from the DXIL ones the verdict would have to change.
  //
  // A DLL built without SPIR-V rejects `-spirv` itself; that reads as
  // "Unknown argument: '-spirv'" and is reported as unsupported rather than
  // silently counted as an -Fc rejection, which would be the same status code
  // for an entirely different reason.
  auto withSpirv = [](std::vector<std::string> v) {
    v.push_back("-spirv");
    return v;
  };
  Observation svbase = runC1("c1-spirv-baseline", withSpirv(extraNoFc), false,
                             false);
  bool spirvOk = svbase.ran && svbase.haveStatus && SUCCEEDED(svbase.status) &&
                 strcmp(svbase.object, "present") == 0;
  Observation svfc, svfcq;
  if (!spirvOk) {
    svfc.name = "c1-spirv-fc";
    svfc.skipped = "this DLL was built without SPIR-V codegen";
    svfcq.name = "c1-spirv-fc-qunused";
    svfcq.skipped = svfc.skipped;
  } else {
    svfc = runC1("c1-spirv-fc", withSpirv(extraFc), true, false);
    std::vector<std::string> sq = withSpirv(extraFc);
    sq.push_back("-Qunused-arguments");
    svfcq = runC1("c1-spirv-fc-qunused", sq, true, false);
  }
  svfc.name = "c1-spirv-fc";
  svfcq.name = "c1-spirv-fc-qunused";

  PrintDetail(c1fc, "IDxcCompiler::Compile, args as filed", fcPath);
  PrintDetail(c1fcq, "IDxcCompiler::Compile, args as filed + -Qunused-arguments",
              fcPath);
  PrintDetail(c1base, "IDxcCompiler::Compile, -Fc removed (ANCHOR)", fcPath);
  PrintDetail(c1dis, "IDxcCompiler::Disassemble on that object (ANCHOR)",
              fcPath);
  PrintDetail(c3fc, "IDxcCompiler3::Compile, argv as filed", fcPath);
  PrintDetail(c3fcq, "IDxcCompiler3::Compile, argv as filed + -Qunused-arguments",
              fcPath);
  PrintDetail(c3base, "IDxcCompiler3::Compile, -Fc removed", fcPath);
  PrintDetail(svbase,
              "IDxcCompiler::Compile, -spirv, -Fc removed (SPIR-V ANCHOR)",
              fcPath);
  PrintDetail(svfc, "IDxcCompiler::Compile, -spirv + args as filed", fcPath);
  PrintDetail(svfcq,
              "IDxcCompiler::Compile, -spirv + args as filed + "
              "-Qunused-arguments",
              fcPath);

  // Leave nothing behind that a later probe could mistake for evidence.
  DeleteFileA(fcPath.c_str());

  const Observation *all[] = {&c1fc,  &c1fcq, &c1base, &c1dis,  &c3fc,
                              &c3fcq, &c3base, &svbase, &svfc,  &svfcq};
  const int caseCount = (int)(sizeof(all) / sizeof(all[0]));
  int ranCount = 0;
  for (const Observation *o : all)
    if (o->ran)
      ++ranCount;

  printf("\n");
  // The c1-* cases plus the disassembly anchor must all have run, on every
  // DLL, or this probe measured nothing. The c3-* cases are allowed to be
  // absent, but only for the one stated reason.
  if (!c1fc.ran || !c1fcq.ran || !c1base.ran)
    return Incomplete("an IDxcCompiler case did not run");
  if (!c1dis.ran)
    return Incomplete(c1dis.skipped.c_str());
  if (c3 && (!c3fc.ran || !c3fcq.ran || !c3base.ran))
    return Incomplete("IDxcCompiler3 is available but a c3 case did not run");
  if (strcmp(c1base.object, "present") != 0)
    return Incomplete("the baseline compile produced no object; the probe "
                      "cannot distinguish 'no disassembly' from 'no compile'");

  printf("SELFCHECK: cases-run=%d/%d\n", ranCount, caseCount);
  printf("SELFCHECK: fc-operand-seen=%s\n",
         extraFc.size() > extraNoFc.size() ? "yes" : "no");
  printf("SELFCHECK: spirv-codegen=%s\n",
         spirvOk ? "available" : "unavailable");
  printf("SELFCHECK: baseline-disassembly-bytes=%zu\n", disasmBytes);
  printf("\n");
  for (const Observation *o : all) {
    if (!o->ran) {
      printf("RESULT case=%s skipped=%s\n", o->name,
             o->skipped.empty() ? "unknown"
                                : (strncmp(o->name, "c1-spirv", 8) == 0
                                       ? "no-spirv-codegen"
                                       : "no-IDxcCompiler3"));
      continue;
    }
    char status[32];
    if (o->haveStatus)
      sprintf_s(status, "0x%08lX", (unsigned long)o->status);
    else
      strcpy_s(status, "n/a");
    printf("RESULT case=%s call=0x%08lX status=%s object=%s disasm=%s "
           "fcfile=%s\n",
           o->name, (unsigned long)o->call, status, o->object, o->disasm,
           o->fcfile);
  }

  if (baselineObject)
    baselineObject->Release();
  if (c3)
    c3->Release();
  c1->Release();
  src->Release();
  lib->Release();
  return 0;
}
