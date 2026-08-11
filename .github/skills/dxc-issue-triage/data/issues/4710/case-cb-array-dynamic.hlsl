// Variant of issue 4710's repro: the reporter's form B -- a resource array declared
// directly inside the cbuffer (no intervening struct, no local struct copy), indexed by
// the same [unroll] loop variable. The issue body says this errors too.
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

float4 psMain() : SV_TARGET0
{
    float4 foo_bar_color = float4( 0.0, 0.0, 0.0, 0.0 );

    [unroll]
    for( int i = 0; i < 4; ++i )
    {
        Texture2D<float4> foo_bar_tex = FooBarTextures   [ i ];

        foo_bar_color += foo_bar_tex[int2(0,0)];
    }

    return foo_bar_color;
}
