# #2673 — expected symptom

*Written before any compiler was run, from the issue text alone.*

**Title:** User command line defines are duplicated in debug info and in preprocessor
**Filed:** 2020-01-30. **Comments:** 0 — the body is the entire report.

## What the report says

Invoking `dxc` with `-D` macro definitions duplicates them "on the way down the pipe from
command line to defines recognized by the preprocessor". Two consequences are claimed:

1. **Debug info** — the defines appear twice in the `!dx.source.defines` metadata list. The
   reporter's quoted node is

   ```
   !71 = !{!"DefineA=1", !"DefineB=0", !"DefineA=1", !"DefineB=0"}
   ```

2. **Preprocessor** — the defines are applied twice, but this is benign: redefining a macro
   to the same value is accepted without a diagnostic. So (2) is *not observable* in compiler
   output; only (1) is measurable. Triage measures (1).

## The configuration dependence, stated up front

The report is explicit that this is **path-dependent**:

> When invoked by the test infrastructure, which skips the initial compile operations found in
> `dxc.cpp`, that's what happens [defines appear once], but when invoked directly from the
> command line, both defines are duplicated.

So:

| path | reporter's claim |
| --- | --- |
| `dxc.exe` driven **from the command line** (goes through `dxc.cpp`) | defines **duplicated** |
| the **API / lit test-infrastructure** path (`IDxcCompiler` etc., skipping `dxc.cpp`'s initial compile operations) | defines appear **once** |

**This triage exercises the command-line path only**, because `triage.py run` invokes
`dxc.exe` with an argument vector — which is precisely the path the reporter says is broken.
A result here must not be generalised to the API path, and the in-tree lit test
(`share_mem_dbg.hlsl`) passing or failing is a statement about the *other* path.

## Repro, as supplied

The issue supplies no inline shader. It names an in-tree file and an invocation:

- file: `tools/clang/test/HLSLFileCheck/dxil/debug/misc/share_mem_dbg.hlsl`
- invocation: "the dxc invocation stipulated by the RUN: command", i.e.
  `%dxc -E main -T cs_6_0 -Zi -Od -DDefineA -DDefineB=0 %s -Qstrip_reflect`

That is exact and resolvable, but it is a *reference* rather than a pasted repro, and `%dxc`
/ `%s` are lit substitutions that have to be expanded by hand. **Repro quality: `partial`** —
supplied and unambiguous, but had to be completed (file copied out of the tree, substitutions
expanded, `| FileCheck` dropped in favour of reading the emitted metadata directly).

Per SKILL.md's #3768 warning about building a repro from a `RUN:` line: here the RUN line
*is* what the reporter cited, so using it is faithful rather than a silent substitution. The
profile stays `cs_6_0` and the flags stay `-Zi -Od -Qstrip_reflect` as written.

## "This reproduces" means

The compile succeeds, emits debug metadata, and the **`!dx.source.defines` node contains each
`-D` define more than once** — concretely, a node listing `DefineA=1` and `DefineB=0` twice
each (four entries for two defines).

## "This does not reproduce" means

The compile succeeds, **emits debug metadata**, and the `!dx.source.defines` node lists each
define exactly once:

```
!{!"DefineA=1", !"DefineB=0"}
```

## The trap this issue sets, recorded before measuring

Debug metadata only exists if `-Zi` (and debug embedding) actually took effect. **"No
`!dx.source.defines` node at all" is not the same as "no duplication".** A predicate shaped as
an absence (`not_regex "DefineA.*DefineA"`) is satisfied for free by any compile that emitted
no debug info — or that failed outright — and would score such a run as *fixed*. The predicate
must therefore be **positive**: it must require the duplicated node to be present, so a
debug-info-less compile scores `no-repro` rather than `repro`, and the notes must separately
confirm that a `no-repro` probe really did emit a single-occurrence defines node.

## Expected verdict shapes

- `repros` — four entries in `!dx.source.defines` for two `-D` flags, on the command-line path.
- `does-not-repro` — two entries, *and* the node demonstrably present.
- `changed-behavior` — the node is present but wrong in some third way (e.g. defines missing,
  or `-D` no longer recorded at all).
- `inconclusive` — debug metadata cannot be obtained at all in the reporter's configuration.

## History expectation

None recorded — deliberately. The transition is what `bisect` is for. Note only that `-Zi`
source metadata (`!dx.source.defines`) is old enough that the v1.4.1907 floor should be able
to express this repro, so a full history is plausible.
