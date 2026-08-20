> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5686](https://github.com/microsoft/DirectXShaderCompiler/issues/5686).

Still reproduces on `main` (89e2f98e2). Compiling `as.hlsl` directly to `-T as_6_6` validates
cleanly; compiling it to `-T lib_6_x` and then `dxc -T as_6_6 -link as.lib` fails with the same
error as reported:

```
Function: main: error: For amplification shader with entry 'main', payload size 8 is greater than declared size of 4 bytes.
```

A full linear scan of all 18 probeable releases from `-link`'s first shipped release
(v1.6.2106, 2021-07) through the current v1.9.2607 reproduces it on every one — there is no
release where it worked, so the bug predates the report by over two years rather than the
other way around. (Three older releases reject `-link` outright as an unknown argument,
confirmed genuinely absent via `--help` rather than a spelling issue, and are excluded from
that range.)

Root cause looks like two separate bugs compounding:

1. `ValidateAsIntrinsics` in `DxilValidation.cpp` computes the amplification shader's payload
   size from `DispatchMesh`'s payload **pointer** type, not the pointee struct — it's missing
   the `->getPointerElementType()` step that the neighbouring mesh-shader check (three lines
   above) does have. So the "declared vs. actual" comparison is really "declared vs. pointer
   size", regardless of the real payload struct.
2. `DxilLinkJob::Link` in `DxilLinker.cpp` builds the linked module and copies the target
   triple, but never calls `setDataLayout` — it never has, in the entire history of that file.
   The linked module falls back to LLVM's default data layout, whose pointer size is 8 bytes,
   versus DXIL's own layout string, which declares 4-byte pointers.

Put together: bug 1 makes the check effectively test "declared payload size >= pointer size"
rather than the real payload size, which is very rarely false for a direct compile (4-byte
DXIL pointer) but always false for anything under 8 bytes once linked (8-byte default
pointer) — independent of whether the payload is actually correctly sized. A payload of 8
bytes or larger would pass either way, correctly sized or not, because the check never
inspects the real struct.

Labels (`bug`, `shader-linking`, `validation`) already look right; no changes suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
