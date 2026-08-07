// microsoft/DirectXShaderCompiler#2191 -- control added during batch-004 collation.
//
// The draft comment claimed the workaround was to REFERENCE the constant in the body.
// Collating this issue against #2188 contradicted that: #2188's variant-scalar-numthreads
// .hlsl uses the same `static const uint` in [numthreads] and compiles clean, yet its body
// never mentions the constant. This isolates the real trigger -- a body containing any
// full expression, referencing nothing relevant -- so the claim is measured rather than
// inferred. Differs from repro.hlsl in exactly one way: the body is non-empty.

RWBuffer<uint> buf;

static const uint eight = 8;
[numthreads(eight, 8, 1)]
void main() { buf[0] = 1; }
