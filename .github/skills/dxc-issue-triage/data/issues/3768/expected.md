# Expected symptom — #3768 "[SPIR-V] crash compiling shader using printf"

**Reported (2021-05-12):** compiling DXC's own SPIR-V test shader
`tools/clang/test/CodeGenSPIRV/intrinsics.printf.hlsl` with `-spirv` crashes with an access
violation. Application Verifier shows heap corruption (`corrupted suffix pattern`) during
`BumpPtrAllocator` slab teardown, so the reported access violation is a *late* symptom of an
earlier overrun.

**Repro quality:** `complete` — the repro is a file in this repository.

**What we test:** `-fcgl -Vd -T cs_6_0 -E main -spirv`. `-fcgl` and `-Vd` are the reporter's,
to disable legalization and avoid an unrelated SPIRV-Tools crash
(KhronosGroup/SPIRV-Tools#4219). The reporter used `-T ps_6_0`; the test file today carries
`[numthreads(1,1,1)]` and its own RUN line says `cs_6_0`, so that is used instead. Record
whether the profile matters.

**Symptom is present if:** DXC fails internally on any run.

**Symptom is absent if:** it compiles cleanly and repeatedly.

**Three reasons this repro is unusually hard to judge, all stated by the reporter:**

1. **It is configuration-dependent.** "If I build locally from source in debug it works. In
   release it works from visual studio but fails on the command line." Our ground truth is a
   **Debug** build — the configuration the reporter says does *not* fail. A clean Debug run is
   therefore **not** evidence the bug is fixed, and must not be reported as such.
2. **It is non-deterministic.** The reporter calls it "a bit inconsistent" and suspects memory
   corruption; unit tests of the same code pass. A single clean run proves nothing — run it
   repeatedly.
3. **Heap corruption does not have to crash.** A silent clean exit is consistent with the bug
   still being present and simply not tripping over. Only a *positive* failure is strong
   evidence here; absence of failure is weak either way.

**Therefore:** test the release binaries too, which are Release builds and closer to the
reported configuration, and repeat runs. Expect the honest verdict to be `inconclusive`
unless a failure is actually observed. Do **not** upgrade "did not crash today" into "fixed".

**Status context:** @s-perron stated in 2024-08 that this is not a priority and invited
outside contribution — so the useful output here is a better-characterised repro, not a
closure recommendation.
