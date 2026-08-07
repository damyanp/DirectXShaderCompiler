# #2673 — notes

**Verdict: `repros`.** Every release from v1.4.1907 (2019-07) to v1.9.2607 (2026-07) and the
ground-truth `main` Debug build duplicate the command-line `-D` defines in debug info, exactly
as filed. History: `always-repro'd`.

## Ground truth

```
dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)
```

Verified against the expected string before anything was run.

## Repro

`repro.hlsl` is a byte-identical copy (sha256 `6C20B1C4…9A6E`) of the file the issue names,
`tools/clang/test/HLSLFileCheck/dxil/debug/misc/share_mem_dbg.hlsl`. `cmd.txt` is that file's
`RUN:` line with the two lit substitutions expanded and the `| FileCheck` pipe dropped;
`cmd-as-filed.txt` holds the original. Profile, `-Zi -Od`, both `-D` flags and
`-Qstrip_reflect` are unchanged — per SKILL.md's #3768 warning, the RUN line *is* what the
reporter cited here, so using it is faithful rather than a silent substitution. Nothing in the
DXC tree was modified or read at run time. **Repro quality: `partial`** — exact and
unambiguous, but a reference rather than pasted code.

## Which path was exercised

**The command-line path only**, i.e. `dxc.exe` invoked with an argv. That is the path the
issue says is affected, and the harness drives it natively. The API path was **not** measured
by running it; the claim about it below rests on source, and is labelled as such.

## Result on ground truth

`out-main-debug.txt`, exit 0, compile succeeds and the DXIL is correct:

```
!dx.source.defines = !{!70}
!70 = !{!"DefineA=1", !"DefineB=0", !"DefineA=1", !"DefineB=0"}
```

Character-for-character the node the reporter quoted, six years later. The same capture also
shows the mechanism one layer up, in `!dx.source.args`:

```
!72 = !{!"-E", !"main", !"-T", !"cs_6_0", !"-Zi", !"-Od", !"-D", !"DefineA", !"-D",
        !"DefineB=0", !"-Qstrip_reflect", !"-D", !"DefineA", !"-D", !"DefineB=0",
        !"-Qembed_debug"}
```

The `-D` pair appears once where it was typed, and a second time appended after
`-Qstrip_reflect`. So the defines are duplicated in the **argument list**, before the
preprocessor or debug info see them — which is precisely what the issue title says
("duplicated … in debug info **and in preprocessor**"). Both nodes are wrong; the issue quotes
only the first.

## Predicate and controls

`match.json` is a positive regex over a metadata *node definition* holding four or more
`Define` entries. Two `-D` flags were passed, so a correct compile yields two entries and
cannot match; the reported duplication yields four and does. It is positive on purpose:
an absence-shaped predicate ("no repeated define") is satisfied for free by a compile that
emitted no debug info at all, and would have reported such a run as fixed.

| control | invocation | expect | result |
| --- | --- | --- | --- |
| `variant-onedefine-main-debug.txt` | one `-DDefineA` | `no-match` | `no-repro` ✔ — node is `!{!"DefineA=1", !"DefineA=1"}`: still duplicated, but two entries, so the predicate stays silent |
| `variant-nodefines-main-debug.txt` | no `-D` at all | `no-match` | `no-repro` ✔ — node is `!{}` |
| `variant-minimal-main-debug.txt` | `control-minimal.hlsl`, identical args | `match` | `repro` ✔ — a four-line compute shader duplicates identically |

The `onedefine` control is the one that earns the predicate: it is a *duplication that the
predicate must not match*, which is what shows the predicate counts occurrences rather than
merely spotting the string `DefineA`. It is also a second measurement in its own right — the
duplication scales with the number of `-D` flags, so it is a blanket re-application of the
whole list, not a quirk of two defines. The `minimal` control shows the defect belongs to the
driver's argument handling, not to the reporter's shader.

## "No debug info" is not "no duplication"

`match-defines-present.json` is the anchor for that distinction: it asks only whether a defines
node carrying any `-D` entry was emitted, so a `no-repro` under `match.json` can be told apart
from a compile that never produced debug information. On ground truth it holds
(`out-main-debug--match-defines-present.txt`).

It was not run across the 20 releases because it cannot add anything there: its regex is a
strict prefix of `match.json`'s, so *every* probe that matched `match.json` necessarily
satisfies the anchor — and all 20 matched. Had any release scored `no-repro`, the anchor would
have had to be run against it before that could be read as a fix.

## History

`bisect --linear` over all 20 bisectable releases (`--linear` rather than the default binary
search so that every release is real evidence rather than two endpoints and an assumption):

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212 v1.7.2212.1
v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407 v1.8.2502 v1.8.2505
v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607          -- all `repro`
```

No `invalid-probe`: every release compiled the repro cleanly (exit 0) and emitted the node.
`out-v1.4.1907.txt` and `out-v1.9.2607.txt` carry byte-identical defines nodes. The floor is
v1.4.1907, so this is "for as long as it is possible to check", not "since 2020" — the issue
predates the floor by six months.

## Source corroboration

This is the strong part of the evidence: the duplication is visible in the code, not only in
the output.

1. **The driver passes the defines twice.** `DxcContext::Compile`
   (`tools/clang/tools/dxclib/dxc.cpp:881-885`) hands `IDxcCompiler::Compile` both `args` —
   built from `m_Opts.Args`, which still contains the user's `-D DefineA -D DefineB=0` — *and*
   `m_Opts.Defines`, the defines the option parser already extracted from those same `-D`
   flags. The `-Fd` sibling call (`:866-870`) does the same. So does the recompile-from-PDB
   path (`:803-806`).
2. **The API layer concatenates rather than reconciles.**
   `DxcCompilerAdapter::WrapCompile` (`tools/clang/tools/dxcompiler/dxcompilerobj.cpp:1877`)
   calls `IDxcUtils::BuildArguments`, which appends the incoming arguments
   (`tools/clang/tools/dxcompiler/dxclibrary.cpp:502-505`) and then appends a fresh `-D <name>`
   pair for every entry of the defines array (`:506-508` → `AddDefines`, `:128-155`). The
   argument list now carries each define twice.
3. **Everything downstream reads that list.** `ReadOptsAndValidate` re-parses it into
   `opts.Defines` (now four entries), `CreateDefineStrings` turns those into the `defines`
   vector (`dxcompilerobj.cpp:685`), which is both fed to the preprocessor one by one
   (`PPOpts.addMacroDef(defines[i])`, `:1484`) and stored as
   `CodeGenOpts.HLSLDefines` (`:1611`), from which `ModuleBuilder`
   (`tools/clang/lib/CodeGen/ModuleBuilder.cpp:303-311`) emits `!dx.source.defines`. That is
   the reporter's "on the way down the pipe … applied twice to the preprocessor" and
   "show up twice in the debug information", as one mechanism.
4. **The same defect was already fixed for `-E` and `-T`, and only for them.**
   `BuildArguments` routes arguments through
   `AddArgumentsOptionallySkippingEntryAndTarget` (`dxclibrary.cpp:157-…`), whose comment reads:
   *"This is used by BuildArguments to skip extra entry/profile arguments in the arg list when
   already specified separatly. This would lead to duplicate or even contradictory arguments in
   the arg list, visible in debug information."* Defines arrive by the identical route and get
   no such treatment. The precedent for the fix is three lines above the bug.

## The configuration dependence, checked

The reporter says the duplication appears from the command line but not "when invoked by the
test infrastructure, which skips the initial compile operations found in `dxc.cpp`". Both
halves still hold, and the second is now structural rather than incidental:

- `tools/clang/test/HLSLFileCheck/lit.local.cfg` sets `config.suffixes = []`, so the whole
  `HLSLFileCheck` tree — including `share_mem_dbg.hlsl` — is **hidden from lit** and is run by
  the TAEF harness instead.
- That harness, `FileRunCommandPart::RunDxc`
  (`tools/clang/unittests/HLSLTestLib/FileCheckerTest.cpp:573-575`), calls
  `pCompiler->Compile(…, flags.data(), flags.size(), nullptr, 0, …)` — the arguments carry the
  `-D` flags, and the defines array is **`nullptr, 0`**. `BuildArguments` therefore appends
  nothing and the defines are recorded once, which is why the file's
  `// CHECK: !{!"DefineA=1", !"DefineB=0"}` passes there.

So the distinction is not really "command line vs API": it is **whether the caller supplies the
defines twice**, once inside the argument array and again through the `pDefines` parameter. Any
API caller that does what `dxc.cpp` does gets the same duplication. This was not measured — no
API-driven probe was run — and is stated from source only.

Consequence worth flagging, since it is the difference between cosmetic and not: this metadata
is what `IDxcPdbUtils` reports as the compile's defines (`dxcpdbutils.cpp:584`) and what the
PIX/DIA surfaces read (`lib/DxilDia/DxcPixCompilationInfo.cpp:87`,
`lib/DxilDia/DxilDiaSession.cpp:51`). `dxc -recompile` reads defines back out of a PDB and
re-passes them (`dxc.cpp:738-761`), which is the same double-supply shape — **not tested here**.

## Compiler Explorer

https://godbolt.org/z/qa68hEf4z — `dxc_1_6_2112` and `dxc_trunk`, both showing
`!{!"DefineA=1", !"DefineB=0", !"DefineA=1", !"DefineB=0"}`. Verified by recompiling the exact
published source and arguments through CE's API (`verify-godbolt.py`, re-runnable) rather than
by trusting the first line of the tool's summary.

CE's own wrapper injects `-Zi -Qembed_debug`, so the `!dx.source.args` node there shows `-Zi`
twice for reasons unrelated to this bug; the banner says so, to stop a reader mistaking it for
the finding. No Clang pane: the defect is in DXC's driver → `IDxcCompiler` plumbing, which has
no counterpart in `hlsl_clang`, so a pane would answer a different question.

## Labels

Currently **none**. Proposed: `bug`, `debug info` — the observable symptom is wrong content in
`!dx.source.defines`/`!dx.source.args`. Deliberately **not** `correctness`: the generated DXIL
is correct, only the recorded defines are wrong, and `correctness` is documented as "bugs that
impact shader correctness". No removals — there is nothing to remove.

## Assessment

Confirmed, unchanged since before the bisection floor, with a mechanism identified in source
and a fix precedent (`AddArgumentsOptionallySkippingEntryAndTarget`) sitting in the same
function. Suggested action: `still-valid-keep-open`. The issue text is accurate in every
particular, including the configuration dependence — `text_stale` does not apply.
