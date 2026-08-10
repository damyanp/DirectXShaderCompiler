# Method notes from 3535 (batch-013)

For a later collation session. Nothing here was applied to shared state.

## 1. `dxa -dumpreflection` is a zero-C++ reflection instrument

2952 concluded that judging a reflection issue needs a host program, and built
`refl2952.exe` for it. That was right for 2952's question (it needed RDAT
fields that no dumper prints), but it should not become the default reflex:
`dxa -dumpreflection` walks `ID3D12ShaderReflection` through DXC's own
`D3DReflectionDumper` and prints every field of every descriptor it reaches.
For any question of the form "does reflection expose X", it answers directly,
and it is built with the tree so there is no harness to write, review, or
trust.

Its limits are worth writing down too: it prints what `D3DReflectionDumper`
chose to print, so an absence in the dump is only evidence about the API if
you also check the dumper's source for whether it calls the accessor at all.
For 3535 that check mattered — `D3DReflectionDumper` never calls
`GetMemberTypeName`, so its absence from the dump would have been ambiguous;
the argument for the API gap rests on there being no route from a signature
parameter to an `ID3D12ShaderReflectionType`, which is a header/source fact.

Suggested for SKILL.md, near the existing "reflection issues need a host
program" material: try `dxa -dumpreflection` first, and read
`lib/DxilContainer/D3DReflectionDumper.cpp` to know what it does not print.

## 2. Reflection-issue history needs a fixed instrument and a varying DLL

`triage.py bisect` substitutes each release's `dxc.exe`. For a reflection
question that measures nothing, because `dxc.exe` never calls a reflection
interface — whatever the predicate reads, it is reading disassembly text.

The pattern that does work (2952 found the same shape from the other
direction) is: hold the instrument fixed and vary the implementation. Copy the
ground-truth `dxa.exe` into a scratch directory together with the release's
`dxcompiler.dll` and `dxil.dll`, and compile the container with that release's
own `dxc.exe`. Windows DLL search order picks up the local `dxcompiler.dll`,
so the reflection implementation under test is the release's.

Measured caveats, all of which held for 20 releases back to v1.4.1907:

* a `main`-built `dxa.exe` loads and drives a 2019 `dxcompiler.dll` without
  complaint;
* the release cache trees contain only `dxc.exe`, `dxcompiler.dll`,
  `dxil.dll`, `dxcapi.h`, `dxcompiler.lib` — there is no `dxa.exe` to use
  instead, which is why the ground-truth one has to be copied in;
* old containers can report `Creator: <nullptr>`, which is not a failure.

## 3. A bisect that reads disassembly can fake a regression on a
   metadata-relocation change

`bisect --linear` on 3535 reported `v1.4.1907 no-repro` then `repro` from
v1.5.2010 onward — the exact shape of a regression, and wrong.

Reflection metadata used to be left in the DXIL part and was moved into the
`STAT` part around v1.5.2010. Any predicate that reads `dxc` stdout is
therefore reading a *different set of metadata* before and after that boundary,
independently of the behaviour under test. Here the pre-v1.5 module still
carried the input struct's field-name annotation, so an absence predicate did
not fire, even though that release's reflection API answered exactly like
every release since.

Generalisation worth adding to the `--linear` / non-monotonic discussion in
SKILL.md: **a transition at v1.4.1907 → v1.5.2010 in a metadata-text predicate
should be assumed to be this relocation until proven otherwise.** It is not
specific to reflection member names; it will bite any predicate that matches
on `!dx.typeAnnotations`, field-name annotations, or the buffer-definitions
block. Confirm by checking whether the same claim holds through an instrument
that does not read the module dump.

## 4. `-Qstrip_reflect` is a general self-test for "is this text
   reflection-derived?"

Useful and cheap: if a string disappears from `dxc` stdout when
`-Qstrip_reflect` removes the `STAT` part, that string is rendered from
reflection data. This turned "the disassembler probably prints reflection"
into a measurement, and it doubles as a control that proves a positive clause
is live. `dxa -listparts` on both containers makes the mechanism visible in
the same transcript.

## 5. On Compiler Explorer, `-Zi -Qembed_debug` is not folklore — the pane
   proves it

SKILL.md warns that CE appends debug flags. The panes carry the proof, which
is much better to cite than the warning:

```
!48 = !{!"-E", !"VS", !"-T", !"vs_6_0", !"-Zi", !"-Qembed_debug"}
```

Consequences worth knowing before choosing panes for an absence-shaped issue:
`!dx.source.contents` embeds the whole source **including the repro's own
comment header**, so quoting the issue in that header manufactures hits; and
`-Zi` keeps reflection metadata in the module, so `!dx.typeAnnotations` is
visible on CE without `-Qkeep_reflect_in_dxil`. The second is a gift — it let
the CE link show the *structural* absence (annotations for the cbuffer struct,
none for the input struct, `%struct.VertexIn` nowhere) instead of relying on a
text search that debug info had already poisoned.

## 6. FXC as the control for "is this a DXC gap or the D3D model?"

`fxc_10_0_19041` is on Compiler Explorer and takes `/T`-style arguments via an
`id:<args>` override. For any "reflection/signature does not expose X" issue it
answers the question a maintainer will actually ask. It pairs well with
`tools/clang/unittests/HLSL/DxilContainerTest.cpp`, which asserts DXC's
reflection equals `d3dcompiler`'s field by field — so "FXC does it too" is not
a coincidence, it is a tested invariant.

One trap found: FXC's listing prints an `// Initial variable locations:` block
that names `vin.mPos`, so the FXC pane also contains the identifier under test.
It is a disassembly annotation, not reflection. Both compilers' panes therefore
contain the string for unrelated reasons, which is worth stating in
`godbolt-note.txt` before a reader searches.

## 7. Tooling observation: the `releases` table schema

`triage.py sql "SELECT ... seed_local FROM releases"` fails with
`no such column: seed_local`. The actual columns are `tag, published_at,
build_date, asset_name, bisectable, prerelease, cached_path`. If SKILL.md or a
docstring mentions `seed_local`, it is stale. `cached_path` is a full path to
`dxc.exe` and points either into `.cache/compilers/releases/<tag>/` or into
`build/tools/clang/test/dxc_releases/<tag>/`, so scripts must use it rather
than assuming a layout.

## 8. Small ones

* Scanning a `.dxo` for an identifier with a raw ASCII search is useless —
  LLVM bitcode packs strings, so `cbAlpha` and `mPos` both return "not found"
  while `POSITION` is found in the `ISG1` string table. Only a real reader
  (`dxc -dumpbin`, `dxa`) can answer.
* PowerShell's `[System.IO.File]::ReadAllBytes('relative')` resolves against
  the *process* working directory, not the shell's `cd`. Use absolute paths.
* Recursive `Select-String` over `lib,tools,include` takes longer than the
  30s default tool wait; scope searches to specific files.
* The ripgrep-based search tool silently returns nothing for anything under
  `.github\` (dot-directories are skipped by default). This reads exactly like
  a true negative. `Select-String` throughout.
