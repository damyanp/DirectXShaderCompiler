// Control: a payload struct with actual members (size 4 bytes: one `uint`).
// This is the ordinary, working case -- DispatchMesh with a real payload is
// what every other amplification-shader test in this repo already exercises
// (tools/clang/test/CodeGenHLSL/mesh-val/amplification.hlsl). The predicate
// in match.json must NOT fire on this: it proves the "payload size N is
// greater than declared size of 0 bytes" diagnostic is specific to the
// empty-struct case, not a broken predicate that matches every AS shader.
struct Payload
{
    uint x;
};

[numthreads(32, 1, 1)]
void main()
{
    Payload pld;
    pld.x = 1;
    DispatchMesh(32, 1, 1, pld);
}
