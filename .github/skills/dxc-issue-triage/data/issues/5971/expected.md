# Expected symptom — #5971 "ASAN alloc_dealloc_mismatch false positive on Ubuntu Linux when using libc++ package"

*Written before any investigation, from the issue text alone (step 2 of the skill).*

Reporter: `amaiorano` (COLLABORATOR), 2023-11-03. Label: `bug`.

## What the issue claims

1. Building and running `check-all` on Linux with ASAN enabled fails at least one test
   (`Clang :: DXC/recompile.test`) with an AddressSanitizer `alloc-dealloc-mismatch` report:
   an allocation attributed to `operator new` (via `std::logic_error::logic_error`) is freed
   via `free` (via `std::invalid_argument::~invalid_argument` / `__cxa_end_catch`), inside
   `DxcIncludeHandlerForInjectedSources::LoadSource` (`tools/clang/tools/dxclib/dxc.cpp:709`).
2. The reporter's own diagnosis: this is **not a real mismatch** — it is a known packaging bug
   in Ubuntu's prebuilt libc++/libc++abi package, where the exception-object allocator used
   internally by libc++abi disagrees with the one libc++ itself uses, producing a false ASAN
   positive whenever an exception object is thrown/caught across that ABI boundary. Cited as
   already known upstream: llvm/llvm-project#52771, llvm/llvm-project#59432, and an Ubuntu
   launchpad bug against `llvm-toolchain-14`.
3. Comment (`amaiorano`, 2023-11-03): workaround is `ASAN_OPTIONS=alloc_dealloc_mismatch=0`,
   to be applied to the `Linux_Clang_Release` bot in `azure-pipelines.yml`. Says this disables
   the check globally but the false-positive class is rare.
4. Comment (`pow2clk`, 2023-11-20): asks whether PR #5976 is the fix, understood as disabling
   the affected tests, and whether this issue tracks "fixing them properly".
5. Comment (`amaiorano`, 2023-11-20): confirms #5976 is the workaround (disabling tests /
   relaxing the check), and says a "proper" fix would require either (a) DXC building its own
   libc++ instead of relying on the Ubuntu package, or (b) waiting for Ubuntu to ship a fixed
   package. Says option (a) was rejected (`llvm-beanz`) as it would increase build times, and
   is unsure about the feasibility of (b).

## What "this reproduces" means

The issue is a **build/CI-environment defect**, not a claim about `dxc`'s compiled output for
any shader: the described alloc/dealloc mismatch is asserted by the reporter to originate in
libc++abi's exception-handling internals on Ubuntu, not in DXC source. There is no HLSL input
whose compiled output could confirm or refute an ASAN false positive that depends on the
platform's C++ runtime ABI packaging.

`repros` (in spirit) would mean: an ASAN-instrumented Linux build of `dxc`/`clang` using the
distribution's packaged libc++, run without the `alloc_dealloc_mismatch=0` workaround, still
raises this specific `alloc-dealloc-mismatch` diagnostic inside `DxcIncludeHandlerForInjectedSources::LoadSource`
(or any other libc++ exception-object path).

`does-not-repro` / fixed would mean: option (a) or (b) from comment 5 above has actually
happened — DXC's CI now builds its own libc++, or the toolchain/package DXC's CI uses has been
upgraded past the point where libc++/libc++abi disagree on the exception-object allocator —
**and** the workaround has consequently been removed from `azure-pipelines.yml`. Merely still
having the `ASAN_OPTIONS=alloc_dealloc_mismatch=0` workaround in place is not evidence either
way about whether the underlying libc++ bug still exists; it only shows the mitigation is
still active.

## Why the compiler is the wrong instrument

There is no `dxc` shader repro here and no HLSL input that could exercise this: the alleged
defect lives in the platform's libc++/libc++abi package (an ASAN interceptor mismatch between
`operator new`/`delete` and `malloc`/`free` inside exception unwinding), triggered by ordinary
C++ exception throw/catch in `dxclib`'s implementation, not by anything shader-source-dependent.
Per the skill's step-5 guidance, the expected status is **`not-compiler-verifiable`**: the
evidence has to be (1) the current CI configuration (does the workaround still exist, and is
it still needed given the toolchain in use), and (2) the upstream libc++ bug reports' own
status, not a compiled-shader diagnostic.

Repro quality (recorded before investigating): **prose-only** — the report is a pasted ASAN
log from a specific bot run plus links to upstream bug reports; there is no shader, no
`cmd.txt`-style invocation, and reproducing it would require an ASAN-instrumented Linux build
against a specific (older, buggy) Ubuntu libc++ package, which is out of scope for this
Windows triage machine and would require rebuilding a shared toolchain.

## Known limitations to state up front

* This triage machine is Windows; there is no ASAN-instrumented Linux `dxc`/`clang` build
  available, and building one is out of scope (no source/build changes, no shared rebuilds
  permitted for this session). Any conclusion is limited to reading the current repo's CI
  configuration and the linked upstream bug trackers' current state.
* The two upstream issues cited by the reporter are on `llvm/llvm-project`, a different public
  repo; their current state (open/closed) is informative context, not proof about what DXC's
  own CI toolchain (a possibly different libc++ package version) does today.
* This is fundamentally a CI/environment tracking issue with a maintainer-acknowledged
  workaround already in place, not a code defect with a bisectable release history.

## What would make this `close-fixed`

Either DXC's CI has switched to building its own libc++ (avoiding the distro package), or the
Ubuntu package/toolchain version DXC's CI now uses has been confirmed to no longer exhibit the
mismatch, **and** the `ASAN_OPTIONS=alloc_dealloc_mismatch=0` workaround has been removed as no
longer necessary. Anything else — including "the workaround is still present and untouched" —
is not fixed; it is the same open tracking state described in the issue's own comments.
