// The non-array constant-expression contexts that FXC can also parse, so the
// two compilers are answering the same question on the same source. FXC has no
// `enum`, so that case lives in case-nonarray-ice-contexts.hlsl instead, and
// the vector dimensions here are kept in range 1..4 so a rejection cannot be
// blamed on `vector<float, 20>` being an illegal type in either compiler.
static const uint2 v2 = uint2(3, 4);

static int gArr[v2.y];

float4 main(uint i : I) : SV_Target
{
    float r = 0;
    switch (i) {
        case v2.x: r = 1; break;
        case 99:   r = 2; break;
    }
    vector<float, v2.y> vv = 0;
    gArr[0] = 1;
    return r + vv.x + gArr[0];
}
