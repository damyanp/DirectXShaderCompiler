# Expected symptom (written before running anything)

Issue: amplification shader (`as_6_5`) whose payload struct declares **no members**
(`struct Payload {};`) and calls `DispatchMesh(x, y, z, pld)` with that empty payload.

Reporter's claim: DXC's DXIL container records a **payload size of 0 bytes** for the
struct (there being nothing to store), but the `dispatchMesh` intrinsic call still
writes/records a nonzero (4-byte) payload size, so DXIL validation fails with:

> For amplification shader with entry 'main', payload size 4 is greater than declared
> size of 0 bytes.

Reporter's link is a third-party site (shader-playground.timjones.io) and is not
reachable from this environment (`No such host is known`), so the repro below is
**agent-constructed** from the issue text and this repository's own amplification-shader
test pattern (`tools/clang/test/CodeGenHLSL/mesh-val/amplification.hlsl`), not a byte-for-byte
copy of the reporter's shader.

**"Reproduces" means:** compiling an amplification shader with an empty-struct payload
(`-T as_6_5`, default validation on) fails with a DXIL validator error naming a payload
size mismatch — i.e. `dxc` emits `internal_failure`-free but validator-rejected output
(nonzero, non-crash exit, `error:` diagnostic quoting a payload-size mismatch), or possibly
a front-end diagnostic rejecting the empty struct outright. Either would count as
"reproduces the reported failure to compile a valid, empty-payload Vulkan-style AS shader".

**"Does not reproduce" means:** the same shader compiles with exit 0 and no validator
error, i.e. an empty-struct payload is accepted and validated as size 0 (or DXC pads it
consistently on both sides of the size check).

Repro quality: **agent-constructed** (issue gives only a description + an unreachable
third-party playground link, no inline HLSL and no attachment).
