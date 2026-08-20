> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5072](https://github.com/microsoft/DirectXShaderCompiler/issues/5072).

**Still reproduces on `main`** (`89e2f98e2`; the local build reports
`1.9.0.5465`), on **all 21 releases I could measure** (v1.4.1907, 2019-07-15,
through v1.9.2607, 2026-07-29), with `-T lib_6_3 -Fh <file>` and no `-Vn`:

```
const unsigned char g_lib.no::entry[] = {
```

exactly the invalid identifier quoted in the report. Feeding that header to
MSVC directly confirms it does not compile, as either C or C++:

```
out-header.h(78): error C2143: syntax error: missing '{' before '.'
out-header.h(78): error C2059: syntax error: '.'
```
```
out-header.h(78): error C2653: 'no': is not a class or namespace name
out-header.h(78): error C2146: syntax error: missing ';' before identifier 'entry'
```

The `-Vn <name>` workaround remains a full fix: the same header, generated
with an explicit name, compiles clean as both C and C++ with no other change.

**#8074**, closed 2026-01-20 as a duplicate of this one, is worth noting here:
it reproduced the identical `g_lib.no::entry` string against `lib_6_5`, and
@damyanp's comment there repeats "we don't plan on scheduling time to work on
this" — so as of ten months ago the team still had this in the same
not-proactively-fixed state described in 2024.

### Cause

`HLSLOptions.cpp` assigns `opts.EntryPoint = "lib.no::entry"` unconditionally
for every library profile — a sentinel meant to be unreachable — and
`dxc.cpp`'s `-Fh` default-name logic (`"g_" + EntryPoint`) has no library-
profile special case, so the sentinel flows straight into the generated
identifier. A non-library `-Fh` case (e.g. `cs_6_0`) is unaffected on every
release measured; the defect is specific to library profiles, not `-Fh` in
general. `git log -S` on the sentinel string finds only its introduction,
`8e21407ca` (2017-05-12, "Add library profile."), never touched since — this
was never a regression to bisect.

No Compiler Explorer link: the bug is entirely inside the `-Fh` file that
CE's API has no channel to return (see `verdict.json`'s `godbolt_skip` for
detail).

Given the workaround has existed the whole time and the maintainer response
already covers the product decision, I'd leave `bug` and `low-hanging-fruit`
as-is and suggest adding `shader-linking` (library-target-specific bug); no
removals.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
