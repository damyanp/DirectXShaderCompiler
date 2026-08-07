// Scope control for #3706's candidate remedy.
//
// repro.hlsl reads a wholly-uninitialized scalar, which -Wuninitialized does report.
// This variant is the PARTIALLY-initialized form: j.x is written, j.y is not, and j.y is
// the index. It answers whether "just enable the warning DXC already has" would cover the
// whole space, or only the wholly-uninitialized case.
struct S {
     uint v;
};

StructuredBuffer<S> stbuf;

uint main() : OUT
{
     int2 j;
     j.x = 1;
     return stbuf[j.y].v;
}
