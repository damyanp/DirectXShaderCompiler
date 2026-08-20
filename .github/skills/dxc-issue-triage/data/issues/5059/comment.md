> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5059](https://github.com/microsoft/DirectXShaderCompiler/issues/5059).

Still not fixed, but the failure mode has changed. Tested on `main`
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, local version `1.9.0.5465`)
with `dxc -T cs_6_3 -ECSMain repro.hlsl` (the maintainer-corrected repro
command; see below on the literal filed command).

**Root cause unchanged.** The loop

```hlsl
while (processed != input) { result += processed; processed++; }
```

still gets rewritten by SCEV into the closed-form
`((input-1)*(input-2))/2`, widened by one bit to `i33` to guard the
intermediate multiply against overflow. Confirmed on `main` with `-Vd`
(validation skipped) that the same illegal sequence is still produced
internally:

```
%7  = zext i32 %6 to i33
%10 = mul i33 %7, %9
%11 = lshr i33 %10, 1
%12 = trunc i33 %11 to i32
```

**What changed:** through `v1.9.2602.24` (2026-05-27) this reached the
disassembly and dxc exited 0 -- a silent correctness bug (exactly the
symptom in this issue). Starting at `v1.9.2607` (2026-07-29), and still
true on `main`, the DXIL validator's `Types.IntWidth` rule now catches it:

```
error: Int type 'i33' has an invalid width.
Validation failed.
```

exit `0x80004005`. Full linear scan shows the silent shape on 19 stable
releases (`v1.4.1907` → `v1.9.2602.24`); only `v1.9.2607` and `main`
show the caught shape -- a single, clean transition. Likely (not certain) source:
[#8207](https://github.com/microsoft/DirectXShaderCompiler/pull/8207)
("Make validator reject unsupported llvm integer sizes", fixing #6563)
extended the width check to ordinary instruction operands, not just
struct members -- but its merge date (2026-03-10) precedes
`v1.9.2602.24`'s build by two months and that release still shows the
old behavior, so attribution to a precise commit isn't proven, only the
release-level bracket is.

Compiler Explorer, `dxc_1_6_2112` (silent) vs `dxc_trunk` (caught) side
by side: https://godbolt.org/z/PGGE6r8s9

Separately, the exact command as filed (`-T lib_6_3 i33.hlsl -Fc
i33.dxil.txt`, no `-E`) no longer reaches this at all on current `main`:
without `[shader("compute")]`, `CSMain` isn't recognized as a library
entry point, so it compiles an *empty* library with only "attribute
ignored" warnings. That command did reach the bug back at `v1.4.1907`
(2019-07), so something about library-mode entry-point recognition
tightened separately at some later, undated point -- a different
question from this one. The maintainer's own corrected repro
(`-T cs_6_3 -ECSMain`, from the second, working godbolt link) is what
still demonstrates the underlying defect today.

Labels look right as-is (`bug, dxil, correctness, validation`); no
changes proposed against the current label taxonomy.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
