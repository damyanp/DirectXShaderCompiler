// mt-harness.cpp -- issue #4792 multithreaded-lockup probe.
//
// Loads dxcompiler.dll dynamically (mirroring a consumer that dlopens
// libdxcompiler.so, as the reporter's build system does) and spins up
// N threads, all released from a single barrier at once, each of which
// creates its own IDxcCompiler3 instance and compiles the same trivial
// HLSL source. This is the first-use cold-start path through
// addHLSLPasses -> PMTopLevelManager::schedulePass ->
// llvm::callDefaultCtor<Pass> -> llvm::initializeXXXPass, i.e. the
// CALL_ONCE_INITIALIZATION macro in include/llvm/PassSupport.h that the
// issue names.
//
// A watchdog thread enforces a bounded timeout: if not every worker
// thread has finished within TimeoutMs, every still-running thread is
// suspended, its instruction pointer resolved against dxcompiler.dll's
// base address, printed, and the process is terminated with a
// distinctive exit code (124) so a driver script can recognize "hung"
// vs. "clean" without waiting forever.
//
// Usage: mt-harness.exe <dxcompiler.dll path> <thread count> <timeout ms> <hlsl file> [dxc args...]
// Exit codes: 0 = every thread's Compile() returned within the timeout
//                 (does not by itself mean every Compile() *succeeded*;
//                 HRESULT/exit-status per thread is printed to stdout).
//             124 = at least one thread did not return within the timeout
//                   (a hang was observed).
//             1 = setup failure (bad args, DLL/proc not found, etc).
#include <windows.h>
#include <dbghelp.h>
#include <psapi.h>
#include <atomic>
#include <cstdio>
#include <string>
#include <vector>

#include "dxcapi.h"

#pragma comment(lib, "dbghelp.lib")

typedef HRESULT(__stdcall *DxcCreateInstanceProc_t)(REFCLSID, REFIID, LPVOID *);

struct ThreadCtx {
  int index;
  HANDLE releaseEvent;
  DxcCreateInstanceProc_t createInstance;
  const wchar_t *sourceName;
  std::string sourceText;
  std::vector<std::wstring> args;
  HRESULT hr = E_FAIL;
  bool compileOk = false;
  DWORD threadId = 0;
  std::atomic<bool> *done;
};

static DWORD WINAPI WorkerProc(LPVOID param) {
  ThreadCtx *ctx = static_cast<ThreadCtx *>(param);
  ctx->threadId = GetCurrentThreadId();
  WaitForSingleObject(ctx->releaseEvent, INFINITE);

  IDxcCompiler3 *compiler = nullptr;
  HRESULT hr = ctx->createInstance(CLSID_DxcCompiler, IID_PPV_ARGS(&compiler));
  if (FAILED(hr) || !compiler) {
    ctx->hr = hr;
    ctx->done->store(true);
    return 1;
  }

  DxcBuffer buf;
  buf.Ptr = ctx->sourceText.data();
  buf.Size = ctx->sourceText.size();
  buf.Encoding = DXC_CP_UTF8;

  std::vector<LPCWSTR> argv;
  for (auto &a : ctx->args)
    argv.push_back(a.c_str());

  IDxcResult *result = nullptr;
  hr = compiler->Compile(&buf, argv.data(), (UINT32)argv.size(), nullptr,
                          IID_PPV_ARGS(&result));
  ctx->hr = hr;
  if (SUCCEEDED(hr) && result) {
    HRESULT status = E_FAIL;
    result->GetStatus(&status);
    ctx->compileOk = SUCCEEDED(status);
    result->Release();
  }
  if (compiler)
    compiler->Release();
  ctx->done->store(true);
  return 0;
}

static void PrintStuckThread(HANDLE hThread, DWORD tid, HMODULE dllModule,
                              const wchar_t *dllPath) {
  SuspendThread(hThread);
  CONTEXT c;
  memset(&c, 0, sizeof(c));
  c.ContextFlags = CONTEXT_CONTROL;
  if (GetThreadContext(hThread, &c)) {
#if defined(_M_X64)
    DWORD64 ip = c.Rip;
#else
    DWORD ip = c.Eip;
#endif
    MODULEINFO mi;
    memset(&mi, 0, sizeof(mi));
    GetModuleInformation(GetCurrentProcess(), dllModule, &mi, sizeof(mi));
    DWORD64 base = (DWORD64)mi.lpBaseOfDll;
    DWORD64 offset = (DWORD64)ip - base;
    if (ip >= base && ip < base + mi.SizeOfImage) {
      wprintf(L"  tid=%lu stuck at dxcompiler.dll+0x%llx\n", tid,
              (unsigned long long)offset);
    } else {
      wprintf(L"  tid=%lu stuck at 0x%llx (outside dxcompiler.dll, base=0x%llx size=0x%lx)\n",
              tid, (unsigned long long)ip, (unsigned long long)base,
              mi.SizeOfImage);
    }
  } else {
    wprintf(L"  tid=%lu: GetThreadContext failed, gle=%lu\n", tid, GetLastError());
  }
}

int wmain(int argc, wchar_t **argv) {
  if (argc < 5) {
    fwprintf(stderr,
             L"usage: mt-harness.exe <dxcompiler.dll> <threads> <timeoutMs> "
             L"<hlsl file> [dxc args...]\n");
    return 1;
  }
  const wchar_t *dllPath = argv[1];
  int numThreads = _wtoi(argv[2]);
  DWORD timeoutMs = (DWORD)_wtoi(argv[3]);
  const wchar_t *hlslFile = argv[4];

  std::vector<std::wstring> baseArgs;
  for (int i = 5; i < argc; i++)
    baseArgs.push_back(argv[i]);

  // Read the HLSL source once; every thread compiles the same bytes.
  FILE *f = nullptr;
  if (_wfopen_s(&f, hlslFile, L"rb") != 0 || !f) {
    fwprintf(stderr, L"cannot open %s\n", hlslFile);
    return 1;
  }
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::string src(sz, '\0');
  fread(&src[0], 1, sz, f);
  fclose(f);

  HMODULE dll = LoadLibraryW(dllPath);
  if (!dll) {
    fwprintf(stderr, L"LoadLibrary(%s) failed, gle=%lu\n", dllPath,
             GetLastError());
    return 1;
  }
  auto createInstance = (DxcCreateInstanceProc_t)GetProcAddress(
      dll, "DxcCreateInstance");
  if (!createInstance) {
    fwprintf(stderr, L"GetProcAddress(DxcCreateInstance) failed\n");
    return 1;
  }

  HANDLE releaseEvent = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  std::vector<ThreadCtx> ctxs(numThreads);
  std::vector<HANDLE> handles(numThreads);
  std::atomic<bool> anyDone[1] = {}; // placeholder, per-ctx atomics below
  std::vector<std::atomic<bool>> doneFlags(numThreads);

  for (int i = 0; i < numThreads; i++) {
    ctxs[i].index = i;
    ctxs[i].releaseEvent = releaseEvent;
    ctxs[i].createInstance = createInstance;
    ctxs[i].sourceName = hlslFile;
    ctxs[i].sourceText = src;
    ctxs[i].args = baseArgs;
    ctxs[i].done = &doneFlags[i];
    doneFlags[i].store(false);
    handles[i] = CreateThread(nullptr, 0, WorkerProc, &ctxs[i], 0, nullptr);
  }

  // Give every thread time to reach the barrier before releasing them,
  // to maximize first-use contention on the pass registry.
  Sleep(200);
  LARGE_INTEGER t0, t1, freq;
  QueryPerformanceFrequency(&freq);
  QueryPerformanceCounter(&t0);
  SetEvent(releaseEvent);

  // WaitForMultipleObjects caps out at MAXIMUM_WAIT_OBJECTS (64), and this
  // harness needs to scale well past that, so poll the atomic done-flags
  // instead of waiting on the thread handles directly.
  DWORD deadline = GetTickCount() + timeoutMs;
  bool allDone = false;
  for (;;) {
    allDone = true;
    for (int i = 0; i < numThreads; i++) {
      if (!doneFlags[i].load(std::memory_order_acquire)) {
        allDone = false;
        break;
      }
    }
    if (allDone)
      break;
    if ((DWORD)GetTickCount() >= deadline)
      break;
    Sleep(20);
  }
  QueryPerformanceCounter(&t1);
  double elapsedMs = (double)(t1.QuadPart - t0.QuadPart) * 1000.0 / freq.QuadPart;

  if (!allDone) {
    wprintf(L"HANG after %.0f ms: not all %d threads returned within %lu ms\n",
            elapsedMs, numThreads, timeoutMs);
    for (int i = 0; i < numThreads; i++) {
      if (!doneFlags[i].load(std::memory_order_acquire)) {
        PrintStuckThread(handles[i], ctxs[i].threadId, dll, dllPath);
      }
    }
    fflush(stdout);
    TerminateProcess(GetCurrentProcess(), 124);
    return 124;
  }

  // All done-flags observed true: threads are finishing up (Release() and
  // return). Reap the handles in batches of <=64 so the process exits
  // cleanly; this should be near-instant since work is already done.
  for (int base = 0; base < numThreads; base += 64) {
    int n = min(64, numThreads - base);
    WaitForMultipleObjects(n, handles.data() + base, TRUE, 5000);
  }

  int okCount = 0, failCount = 0;
  for (int i = 0; i < numThreads; i++) {
    if (ctxs[i].compileOk)
      okCount++;
    else
      failCount++;
  }
  wprintf(L"CLEAN in %.0f ms: threads=%d ok=%d failed-compile=%d\n", elapsedMs,
          numThreads, okCount, failCount);
  if (failCount > 0) {
    int shown = 0;
    for (int i = 0; i < numThreads && shown < 5; i++) {
      if (!ctxs[i].compileOk) {
        wprintf(L"  sample failing thread[%d]: hr=0x%08lx\n", i,
                (unsigned long)ctxs[i].hr);
        shown++;
      }
    }
  }
  return 0;
}
