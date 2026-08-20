# Issue 4805 — expected symptom

**Title:** Compiler does not use the custom include handler when compiling with `-Zi`
**Filed:** 2022-11-20 by `bitsauce`. **Comments: 2.** Labels: `bug`, `api`.

This prediction is derived from reading `tools/clang/lib/SPIRV/EmitVisitor.cpp`
(`ReadSourceCode`, `getChoppedSourceCode`, `EmitVisitor::visit(SpirvDebugSource*)`)
and its git history *before* the corrected harness was run to completion against
ground truth. A note on chronology, in the interest of not silently back-filling
this file to match whatever came out: an early build of the harness (with a
since-fixed candidate-matching bug) was compiled and run once, purely to shake
out the harness itself, before this file was written; that run failed with a
plain "file not found" parse error and produced no evidence about the actual
defect either way. The source-code read that produced the prediction below came
first and is unaffected by that run. The full, decisive 3-way experiment
described here (no-disk / mismatched-disk / identical-disk) had not yet been run
when this file was written.

## What the issue says

A custom `IDxcIncludeHandler` (case-insensitive-with-both-styles, like C++:
serves files either relative to a global shader root or relative to the
including file) is supplied to `IDxcCompiler::Compile`. Compiling
`Passthrough.hlsl` (which `#include`s `Includes/Uniforms.hlsl`) with
`-Zi`/`-fspv-debug=source` **crashes** when the process's current working
directory is the parent of the shader tree, even though the custom handler can
resolve the include either way; it works when CWD is the shader directory. The
reporter attributes this to "the include handler is not used in some parts of
the compilation process" and attaches a callstack terminating in
`EmitVisitor.cpp`'s `ReadSourceCode` → `DxcCreateBlobFromFile` →
`ReadBinaryFile`. A 2024 maintainer comment (`llvm-beanz`) says this "doesn't
seem SPIR-V specific, seems like a tooling problem" (not independently
investigated here — the DXIL side uses a differently-shaped, non-ASCII debug
container that this harness's byte-search cannot evaluate; see "What would
make this unmeasurable"). A second reporter (`leozzyzheng`, 2025-11-19)
confirms "the custom include handler is ignored when compiling with -Zi", with
no crash mentioned.

## Root cause, read from source before running anything

`ReadSourceCode(filePath, spvOptions)` (`EmitVisitor.cpp:~136`) is called from
two places that build the SPIR-V rich debug info (`NonSemantic.Shader.DebugInfo.100`
`DebugSource`/`OpString`) for **every** file with debug info, including files
that were `#include`d through the caller-supplied handler. It does **not**
receive or reuse whatever buffer the include handler already returned to the
parser. Instead it does its own, independent, freshly-initialized
`IDxcLibrary::CreateBlobFromFile` raw disk read of `filePath` — the *resolved*
path (relative to the including file's directory, confirmed empirically — see
"front-end candidate spelling" below), inside a `try { } catch (...) { return
"" (or, for the main file only, `origSource`); }`. So:

* If that raw disk read happens to find a file at the resolved path, its
  content — not the handler's content — is what gets embedded, silently, with
  no diagnostic that anything was substituted.
* If it does not find a file there (the reporter's exact scenario — a custom
  handler resolving a path that has no matching entry on disk, or a purely
  in-memory-served include), the catch fires and, for anything other than the
  main file, an **empty** string is embedded. There is no code path that falls
  back to what the include handler supplied.

Either way, the include handler's actual content is never the thing embedded
in `DebugSource` for an included file. This is a defect in the *debug-info
source-embedding* step specifically, not in `#include` resolution: a quick
empirical check (`dxc.exe -Fc` against real on-disk files) already shows the
front end resolves and parses the include correctly; only the later,
independent re-read misses it.

The try/catch itself (so *some* graceful, non-crashing handling of a
disk-read failure) has existed since 2020-09-22 (`7f985ff47`, #3155),
**before** this issue was filed (2022-11-20). Commit `97b5edbc4398317a6c50437cee06393c1fd94b74`
(2025-07-24, PR #7662, "[SPIRV] Fix DebugSource for files which are not
found") narrowed the fallback-to-`origSource` condition so it only applies to
the main file (previously it applied to *any* file whenever `origSource` was
non-empty — meaning, before #7662, a disk-read failure on an *included* file
would silently substitute the **main file's** text as if it were the included
file's `DebugSource`, a different and arguably worse form of the same defect).

## Predicted classification, stated now so it cannot be rationalised later

* **The core defect — "custom include handler content is not what gets
  embedded as an included file's SPIR-V `DebugSource`" — is predicted to
  `repros`, unconditionally, on `main-debug`.** The code path that would need
  to exist to make it not reproduce (reusing the parser's already-fetched
  buffer instead of re-reading disk) does not exist anywhere in
  `EmitVisitor.cpp`.
* **The literal reported symptom — a crash** — is predicted **not** to
  reproduce on `main-debug` as a plain unhandled fault, because the
  disk-read-failure path has been wrapped in `catch (...)` since before the
  issue was filed. I expect either a clean compile with silently-empty/wrong
  debug source (today's likely shape, matching the second commenter's
  "ignored" wording with no crash), or — only if a same-named-but-different
  file genuinely exists on disk at the resolved candidate path — some other
  compile-time consequence of embedding mismatched content (column/line
  references computed against the parsed buffer, but checked/rendered against
  a different re-read buffer). I flag this second scenario as worth testing
  explicitly, but do not yet know its shape.
* Honest overall status is most likely **`changed-behavior`**: the underlying
  "handler ignored for debug source" defect persists exactly as reported, but
  its user-visible shape has apparently softened from "crash" (2022, no
  try/catch narrowing yet) to "silent wrong/empty content" — `repros` would
  be defensible too if the crash-shaped symptom turns out to still occur
  under some variant I haven't tried yet, or if any variant of the
  mismatched-content case turns out to fail the compile outright (which
  would itself be a *further* changed shape, not a return to the original
  crash).
* `not-compiler-verifiable` is explicitly **rejected**: this is reachable by a
  compiled program calling the public `IDxcCompiler::Compile` C++ API exactly
  as the reporter describes doing in their own application. `dxc.exe` itself
  cannot exercise it (its command-line driver only ever builds its own
  disk-backed default handler, so the substitution point is unreachable from
  the CLI no matter how CWD/`-I` are varied) — that is why a harness
  (`handler4805.cpp`) is required, per SKILL.md's harness-as-compiler pattern,
  not evidence that the defect is unverifiable.
* `inconclusive` only if the byte-search methodology itself cannot be trusted
  — ruled out by a same-run identical-content positive control that must show
  the marker present, proving the harness, the API path, and the search all
  work.

## Anti-vacuity requirements

* **Positive control (identical-content):** a real on-disk file at the exact
  resolved candidate path, byte-for-byte identical to what the custom handler
  serves. The container **must** show the marker present here, or nothing
  else in this repro means anything (a broken harness/byte-search would
  silently show "absent" everywhere, indistinguishable from the real bug).
* **Self-consistency:** the harness logs every `LoadSource` candidate string
  requested, so "the handler was never asked" is distinguishable in the
  transcript from "the handler was asked, answered, and was still ignored."

## Repro quality

**`prose-only` as filed** — the body describes the reporter's own application
code and a callstack, but ships no shader files, no harness, no attachment.
Recording as `agent-constructed`: the repro shader (mirroring the reporter's
exact file layout) and the entire custom-`IDxcIncludeHandler` harness are
built for this triage.

## What would make this unmeasurable

* If `dxc.exe`'s own command-line driver could somehow be coerced into using a
  non-disk-backed handler, that would be a better repro than a harness; it
  cannot (confirmed by reading `dxcompiler`'s CLI wiring — it always
  constructs its own default handler).
* DXIL's `-Zi -Qembed_debug` analogue is **out of scope for a firm
  conclusion**: a same-shaped byte-search control (disk content byte-identical
  to the handler's content) did **not** show the marker present in the DXIL
  container, meaning the DXIL debug-info container does not store source text
  as a contiguous ASCII run the way SPIR-V's `OpString` does (most likely a
  compressed/PDB-shaped embedding). Without a working positive control this
  harness cannot assert anything about the DXIL side, and it is not extended
  further here. This directly informs (but does not resolve) `llvm-beanz`'s
  "not SPIR-V specific" comment.
