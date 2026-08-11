// Case for issue 4710: a GENUINELY dynamic index into the same cbuffer resource array --
// the index comes from a shader input, so no unrolling or constant folding can turn it
// into a literal. This is the case DXC's own regression tests
// (tools/clang/test/HLSLFileCheck/hlsl/resource_binding/res_in_cb3.hlsl and
// .../objects/CbufferLegacy/resource-in-cb4.hlsl) assert the diagnostic for, and it is
// the case the diagnostic is plainly *right* about. It separates "DXC rejects dynamic
// indexing of cbuffer resource arrays" from "DXC rejects an index that is a literal after
// [unroll]".
// Expect: match.
struct FooBarInfo
{
    float Scalar;
    Texture2D<float4> Texture[4];
};

cbuffer cbFooBar
{
    FooBarInfo        FooBars[4];
    Texture2D<float4> FooBarTextures[4];
};

Texture2D<float4> NotFooBarTextures[4];

float4 psMain( uint i : I ) : SV_TARGET0
{
    Texture2D<float4> foo_bar_tex = FooBarTextures[ i ];
    return foo_bar_tex[int2(0,0)];
}
