> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5269](https://github.com/microsoft/DirectXShaderCompiler/issues/5269).

Still reproduces on `main` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df), and on every stable
release since amplification shaders shipped (v1.5.2010 through v1.9.2607) — this has never
worked, it is not a regression. Compiling

```hlsl
struct Payload
{
};

[numthreads(32, 1, 1)]
void main()
{
    Payload pld;
    DispatchMesh(32, 1, 1, pld);
}
```

with `-T as_6_5 -E main` gives the same diagnostic quoted in the issue:

```
error: For amplification shader with entry 'main', payload size 4 is greater than
declared size of 0 bytes.
```

Compiler Explorer: https://godbolt.org/z/WfqfzrK91 (`dxc_1_6_2112` and `dxc_trunk`, identical
result on both).

The root cause is a one-line bug, not a broader design gap. In
`ValidateAsIntrinsics` (`lib/DxilValidation/DxilValidation.cpp`), the first payload-size
check reads the size of the **payload pointer** instead of the pointee struct:

```cpp
Value *OperandVal = DispatchMeshCall.get_payload();
Type *PayloadTy = OperandVal->getType();          // pointer type, not pointee
unsigned PayloadSize = DL.getTypeAllocSize(PayloadTy);
```

DXIL's datalayout uses 32-bit pointers, so `PayloadSize` here is always the constant 4,
regardless of the real payload size — which is why every ordinary (non-empty) payload
struct in this repo's own test suite is at least 4 bytes and never trips the bug: the
comparison `declared < 4` is false for them. An empty struct is the one case whose real
size (0, confirmed by the DXIL metadata this build itself emits) is less than that
constant, so the check fires on exactly the input this issue reports. A second,
correctly-written check 40 lines later in the same function does strip the pointer, which
is what confirms the first one doesn't.

Whether DXC should accept a zero-byte amplification-shader payload at all (matching
Vulkan's optional task-payload semantics) is a separate design question this triage
doesn't decide. But independent of that policy call, the validator's own bookkeeping is
inconsistent here: it records a declared size of 0 for this payload and then rejects it
by comparing against the wrong operand.

Suggested label: `validation` (the defect is in the DXIL validator's own payload-size
accounting, not in front-end acceptance or codegen).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
