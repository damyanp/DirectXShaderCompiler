// Repro for https://github.com/microsoft/DirectXShaderCompiler/issues/4710
// Verbatim from the issue body (form A active: foo_bar.Texture[i]).
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
        FooBarInfo        foo_bar     = FooBars          [ i ];
        Texture2D<float4> foo_bar_tex = foo_bar.Texture  [ i ];

        foo_bar_color += foo_bar_tex[int2(0,0)] * foo_bar.Scalar;
    }

    return foo_bar_color;
}
