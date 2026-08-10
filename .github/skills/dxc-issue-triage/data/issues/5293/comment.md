> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5293](https://github.com/microsoft/DirectXShaderCompiler/issues/5293).

@rbertin-aso — the exact `TRayVsAABB` function you pasted compiles cleanly here
(exit 0), which helps narrow the search. Its `out T2 intersections` is a vector,
and this analysis tracks only scalar `out` parameters. Adding one scalar
`out T` to that same function asserts immediately. The function triggering the
crash in your shaders is therefore likely another template with a scalar
`out` (`float`, `uint`, `bool`, ...) and at least one local.

**The issue itself still reproduces.** Confirmed on a local **Debug** build of
`13730886e` (1.9.0.5433), and the underlying defect is present in every shipped
release from **v1.7.2308 through v1.9.2607**. A second trigger may explain “it
was not crashing before” without a compiler change: crossing from 28 to 29
tracked locals turns the latent out-of-bounds access into a Release crash.

### Why this looked "harmless" for so long

Running the description's example against all 20 catalogued releases gives exit 0 every time.
That is not a fix — every release is a **Release** build, so the assert is compiled out, and
that example is small enough to survive the aftermath.

@simontaylor81 wrote in May 2024 that with the assert gone the valueless `Optional` is read
anyway and used to index a vector out of bounds. That is measurable, and it is what happens:

```
Optional::getValue          assert(hasVal)
Optional::getPointer
SmallBitVector::operator[]  "Out-of-bounds Bit access."
SmallBitVector::set         "undefined behavior"
```

`scratch` is `PackedVector<Value, 2, SmallBitVector>`, and `SmallBitVector` keeps its bits
inline only while they fit in `SmallNumDataBits = 57` — that is **28** two-bit entries. Past
that it heap-allocates, and the out-of-bounds index stops being a harmless masked shift and
becomes a wild pointer dereference.

So the number of local variables in the function decides which symptom you get. Taking the
description's example and varying only that, on the **shipped v1.9.2607 release binary**:

| locals | exit |
| --- | --- |
| 27 | `0x00000000` |
| 28 | `0x00000000` |
| **29** | **`0xC0000005`** (access violation) |
| 30, 32, 40, 64, 120 | `0xC0000005` |

Same binary, same construct — one shader compiles, the next crashes. Controls on that same
binary: removing the template, or changing `out` to `inout`, gives exit 0 in every case, so
this is this defect and not "a big function".

**This may be why it "was not crashing before" without any compiler upgrade on your side:**
adding a couple of locals to an already-affected templated function is enough to cross that
threshold. The bug is latent well before it becomes visible.

### Which releases are affected

| releases | behaviour |
| --- | --- |
| v1.4.1907 – v1.6.2106 | cannot compile the repro at all (no `-HV 2021`) — no evidence either way |
| v1.6.2112 – v1.7.2212.1 | clean, because the analysis containing the defect does not exist yet |
| **v1.7.2308 – v1.9.2607** | **crash (`0xC0000005`), all 12 releases** |

The boundary is `1380cf88e` ("Add diagnostics for uninitialized `out` parameters", #5047),
first shipped in v1.7.2308. Two independent checks agree on it: whether the release emits
`-Wparameter-usage` at all, and `git merge-base --is-ancestor`.

Reproduced on Compiler Explorer, which runs **Release** builds — so it speaks to the
configuration you are shipping: <https://godbolt.org/z/MKsnrdq4T>

```
dxc 1.7.2212   exit 0
dxc 1.7.2308   SIGSEGV
dxc trunk      SIGSEGV
```

The workarounds from the description still hold, all three verified here: drop the template,
use `inout` instead of `out`, or have no locals in the function. `inout` is usually the
smallest change.

### Root cause

`DeclToIndex::computeMap()` builds its index from the DeclContext's declarations. For a
**function-template instantiation** the `out` parameter is not among them, so the lookup for
the assignment returns an empty `Optional` —
`tools/clang/lib/Analysis/UninitializedValues.cpp:232`, reached via
`Sema::InstantiateFunctionDefinition` → `AnalysisBasedWarnings::IssueWarnings` →
`runUninitializedVariablesAnalysis`. That single fact accounts for all three workarounds.

PR #8401 appears to target this and is open, not merged, as of writing.

### Scope of this testing

The assert was observed on a local **Debug** build; the crash figures come from the shipped
**Release** binaries and from Compiler Explorer, which is also Release. The large-locals
shader used to expose the Release crash is one I constructed to make the symptom
deterministic — it is not anyone's reported code. I have not tried to reproduce the specific
crash in the Asobo or Frostbite shaders themselves, only to establish the mechanism and the
affected range.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
