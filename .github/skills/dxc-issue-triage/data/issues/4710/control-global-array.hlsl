// Control for issue 4710: the reporter's own form C -- a resource array declared at
// GLOBAL scope, indexed by the same [unroll] loop variable. The reporter states this
// "Works in DXC & FXC". If this errors, the instrument is wrong, not DXC.
// Expect: no-match.
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
        Texture2D<float4> foo_bar_tex = NotFooBarTextures[ i ];

        foo_bar_color += foo_bar_tex[int2(0,0)];
    }

    return foo_bar_color;
}
