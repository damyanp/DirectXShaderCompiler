# Issue 4514 — "Variable inside a namespace not found"

**Verdict: reproduces, and has reproduced on every stable release that can be
probed (v1.4.1907 .. v1.9.2607, 20 releases) plus current `main`.**

Ground truth: `main-debug`, `dxc` 1.9.0.5433, public commit `13730886e`.
The binary self-reports a different commit in its version string
(`1.9.0.5433 (triage, ab5400907)`) because it was built from a working branch;
`git diff --name-only ab5400907 13730886e` shows no file outside
`.github/skills/dxc-issue-triage/`, and the control diff against
`13730886e~50` does list files outside it, so the query can detect differences
and the equivalence is real rather than an artefact of a broken query.

## The repro

`repro.hlsl` is the issue body's shader, verbatim, with no edits.
`cmd.txt` is `-T cs_6_0 -E main repro.hlsl`. Profile and entry point are the
only things the report leaves implicit, and `[numthreads(1,1,1)]` +
`void main(...)` fix them unambiguously. Repro quality: **complete**.

`match.json` is a single `contains` clause quoting the reporter's own error
text verbatim:

```
no member named 'testVariable' in namespace 'testNamespace'
```

Verbatim matters twice here. First, this is a diagnostic-quality issue, and
`classify()` lists `no member named` among its feature-absence markers — an
approximated predicate would have had *every* reproducing release demoted to
`invalid-probe` and `bisect` would have reported "no release could run this
repro". Quoting the marker inside a positive clause is what suppresses that
(`_predicate_quotes`, SKILL.md's #3055 note). No capture in this directory
carries an `# invalid-probe-reason:` header, which is the on-disk confirmation
that the demotion never fired. Second, the clause names both the namespace and
the member, so it is self-anchoring: a build that rejected the input before
reaching name lookup cannot emit it, and a shader that never declared
`testVariable` inside `testNamespace` cannot provoke it.

## Ground truth

```
repro.hlsl:15:9: error: no member named 'testVariable' in namespace 'testNamespace'; did you mean simply 'testVariable'?
    if( testNamespace::testVariable * tid.x > 0 )
        ^~~~~~~~~~~~~~~~~~~~~~~~~~~
        testVariable
repro.hlsl:5:14: note: 'testVariable' declared here
```

Exit `0x80004005` (E_FAIL) — an ordinary diagnosed error, not an internal
failure. Word-for-word the message the reporter quoted in 2022.

## The `-HV` hazard: measured, and the flag is inert

The report names no language version, so `cmd.txt` carries none. That decision
was tested rather than assumed, in both directions:

| flag | result |
| --- | --- |
| none (today's default, `-HV 2021`) | repro |
| `-HV 2016` | repro (`variant-hv2016-main-debug.txt`) |
| `-HV 2017` | repro |
| `-HV 2018` — the reporter's Dec-2021 default | repro |
| `-HV 2021` explicitly | repro |

The symptom is identical under every language version DXC accepts, so `-HV` is
**not load-bearing** and adding one would have been pure downside: older
releases answer `Unknown HLSL version: 2021`, which is an `invalid-probe`, and
that would have manufactured a version floor and made every release below it
look as though it had fixed the bug. The forward-in-time mirror is also clear —
the current `-HV 2021` default does not reject this 2022 shader for any
unrelated reason, so the `main` result means what it appears to mean.

## Release history — linear scan, all 20 stable releases

`bisect --linear`, so the claim is a population claim and not an inference from
two agreeing endpoints:

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212
v1.7.2212.1 v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407
v1.8.2502 v1.8.2505 v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607
```

All 20 score `repro`; 21 of 21 captures in this directory carry
`# verdict: repro`; **no invalid probes**, and no release needed an
option-spelling retry. Five probeable prereleases (`v1.5.2003`,
`v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`,
`v1.10.2605.24`) were excluded by policy; the issue names none of them, so no
`release-policy.json` opt-in applies. `v1.2.0-alpha` ships no usable `dxc`.

v1.4.1907's output is byte-identical to `main`'s apart from the file path, so
the diagnostic has not been reworded in seven years and no text-portability
problem arises. v1.4.1907 (2019-07-15) is the bisection floor and predates the
report by three years, so the honest statement is **"has reproduced for as long
as it is possible to check"**, not "since it was filed".

Source dating agrees: the line responsible (below) has been present since
`6ee4074a4`, the repository's first commit (2016-12-28), so the defect predates
every probeable release.

## Root cause

Two source facts, both literal code in this tree:

1. `HLSLBufferDecl::Create` hardcodes the semantic `DeclContext` of every
   `cbuffer`/`tbuffer` to the translation unit
   (`tools/clang/lib/Sema/SemaHLSL.cpp:15420`):

   ```cpp
   DeclContext *DC = C.getTranslationUnitDecl();
   HLSLBufferDecl *result = ::new (C) HLSLBufferDecl(DC, ...);
   if (DC != lexicalParent)
     result->setLexicalDeclContext(lexicalParent);
   ```

   The enclosing namespace is only the buffer's **lexical** parent.

2. `HLSLBufferDecl` is a transparent context
   (`tools/clang/lib/AST/DeclBase.cpp:913`), so
   `makeDeclVisibleInContextWithFlags` republishes the buffer's members into
   `getParent()` — the *semantic* parent, i.e. the translation unit
   (`DeclBase.cpp:1586-1589`).

So `testVariable` is made visible in the TU and never in the namespace, which
is exactly the reported asymmetry: unqualified lookup finds it, and qualified
lookup into `testNamespace`'s `DeclContext` finds nothing and produces the
error.

Two independent measurements corroborate the DeclContext claim without relying
on reading the code:

- `dxc -ast-dump` prints `HLSLBufferDecl 0x… parent 0x…` where the printed
  parent is the `TranslationUnitDecl`'s address — the dumper only prints
  `parent` when lexical and semantic contexts differ
  (`tools/clang/lib/AST/ASTDumper.cpp:1125-1126`).
- Debug info, emitted by an unrelated part of the compiler:
  `variant-fix-texture-debuginfo-main-debug.txt` has
  `!DIGlobalVariable(name: "testVariable", linkageName:
  "\01?testVariable@testBuffer@@3IB", scope: !0 …)` where `!0` is the compile
  unit, next to `!DIGlobalVariable(name: "testTexture", … scope: !23)` with
  `!23 = !DINamespace(name: "testNamespace")`. The namespace is missing from
  both the debug scope and the mangled name. Compiler Explorer's Linux Release
  build emits the same two records, so this is not a Windows or Debug artefact.

### Why the reporter's workaround works

`buildLookupImpl` recurses into transparent inner contexts
(`DeclBase.cpp:1364-1366`), and that recursion *does* add the buffer's members
to the enclosing namespace's lookup map. It only ever runs if something marked
the namespace as having local lexical decls to build; with nothing in the
namespace but the cbuffer, `LookupPtr` stays null and `DeclContext::lookup`
returns an empty result outright (`DeclBase.cpp:1424`). The extra `Texture2D`
is a declaration whose semantic context genuinely *is* the namespace, so it
sets `HasLazyLocalLexicalLookups` (`DeclBase.cpp:1583`) and the later lookup
builds the table — picking up the cbuffer member as a side effect.

That reading makes four predictions. All four were written into the control
shaders **before** running them, and all four hold:

| control | prediction | measured |
| --- | --- | --- |
| `control-dummy-static.hlsl` — `static uint` in the namespace | clean | clean (exit 0) |
| `control-dummy-struct.hlsl` — a `struct` in the namespace | clean | clean (exit 0) |
| `control-two-cbuffers.hlsl` — a *second* cbuffer, nothing else | **still fails** | still fails |
| `control-reopen-after.hlsl` — the extra decl moved below `main()` | **still fails** | still fails |

The last two are the discriminating cases. A second cbuffer does not help,
which rules out "any extra declaration fixes it" — both buffers get the TU as
their semantic parent. And moving the helping declaration *after* the use
re-breaks it (`control-reopen-before.hlsl`, the same text with the block above
`main()`, compiles clean), which is what pins the mechanism specifically on a
lookup table built lazily at the point of use.

Practical consequences worth stating: the workaround is **position-dependent**
and has nothing to do with textures — any prior namespace-scope declaration
does it. `tbuffer` is affected identically (`control-tbuffer.hlsl`), which
follows from both kinds sharing that one `Create`.

## Controls

All ground-truth controls carry a declared `--expect`, so `reindex` re-checks
them permanently.

| capture | expect | result |
| --- | --- | --- |
| `variant-fix-texture-*` — the reporter's workaround | no-match | clean, exit 0 |
| `variant-unqualified-*` — unqualified reference | no-match | clean, exit 0 |
| `variant-global-cbuffer-*` — cbuffer at global scope | no-match | clean, exit 0 |
| `variant-dummy-static-*`, `variant-dummy-struct-*` | no-match | clean |
| `variant-two-cbuffers-*`, `variant-reopen-after-*`, `variant-tbuffer-*` | match | reproduce |
| `variant-reopen-before-*` | no-match | clean |
| `variant-hv20{16,17,18,21}-*` | match | reproduce |
| `variant-ce-source-{plain,workaround,unqualified}-*` | match / no-match / no-match | as expected |

The first two reproduce the two statements the thread makes about behaviour —
the reporter's ("uncommenting fixes it") and hekota's ("recognized only by its
unqualified name") — and both hold exactly. The third shows the predicate does
not fire on ordinary constant buffers.

The `variant-ce-source-*` trio is the transformation control required before
publishing a rewritten repro: the preprocessor-guarded source published to
Compiler Explorer was first run locally in all three configurations and behaves
identically to `repro.hlsl`, so the guards are not the subject.

## Compiler Explorer

https://godbolt.org/z/1497YdPj1 — five panes, read back through
`/api/shortlinkinfo/1497YdPj1` and confirmed to hold the arguments claimed.
Full pane text is in `manual-case-godbolt-verify.txt`.

| pane | result |
| --- | --- |
| `dxc_1_6_2112 -T cs_6_0 -E main` | the reported error (exit 5 = E_FAIL truncated by Linux) |
| `dxc_trunk` | the same error |
| `dxc_trunk -DWORKAROUND` | exit 0, clean DXIL |
| `hlsl_clang_trunk -fsyntax-only` | **exit 0 — Clang accepts the qualified name** |
| `hlsl_clang_trunk -fsyntax-only -DUNQUALIFIED` | exit 1 — Clang *rejects* the unqualified name |

`dxc_1_6_2112` is CE's oldest DXC and is also the "December 2021" build the
report names, so the first pane is the reporter's own version.

The two Clang panes are the interesting result: the successor front end behaves
**inversely** to DXC on this construct. It resolves
`testNamespace::testVariable` and rejects a bare `testVariable` with
`use of undeclared identifier 'testVariable'; did you mean
'testNamespace::testVariable'?`. Pane 5 is pane 4's control: because it errors
on the same input under the same flags, pane 4's exit 0 is a real acceptance
rather than a pane that never compiled anything. `dxc_trunk` and
`hlsl_clang_trunk` are rolling builds, so this dates nothing; it is a statement
about the class of behaviour, not about a revision.

## Verdict

- **status** `repros`
- **repro quality** `complete`
- **history** always reproduced across v1.4.1907..v1.9.2607, all 20 stable
  releases probed linearly, no invalid probes; predates the bisection floor
- **confidence** `high`
- **suggested action** `still-valid-keep-open`
- **text-stale** none. The issue was filed in 2022 and every claim in it —
  the shader, the error text, the workaround — still measures exactly true, and
  the most recent maintainer comment (2025-04-22) is also accurate.

Not `close-fixed` under any reading, and not a candidate for one: nothing in
20 releases has ever compiled this shader.

## What I did not measure

- I did not attach a debugger to observe `HasLazyLocalLexicalLookups` toggling.
  The lazy-lookup half of the explanation rests on reading `DeclBase.cpp` plus
  the four behavioural predictions above, three of which (the two negative
  cases and the position dependence) would have falsified it. It is strong, not
  proven.
- I did not test FXC. FXC does not support `namespace`, so a pane would have
  measured the absence of the feature rather than a disagreement about it.
- I did not test `ConstantBuffer<T>` or `RWBuffer`-style declarations inside a
  namespace, so "affects cbuffer and tbuffer" is exactly the scope measured —
  not a claim about every resource kind.
- Compiler Explorer runs Linux Release builds and appends its own
  `-Zi -Qembed_debug -Fc -`; it corroborates the local Windows Debug build here
  and does not overrule it.
