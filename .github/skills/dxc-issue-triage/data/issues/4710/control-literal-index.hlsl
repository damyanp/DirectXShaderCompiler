// Control for issue 4710: the SAME resource array inside the SAME cbuffer, indexed by
// literal constants instead of the loop variable. This differs from the repro in exactly
// the property the diagnostic names ("must be a literal expression"), so it is the
// strongest negative control available.
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

    foo_bar_color += FooBars[0].Texture[0][int2(0,0)] * FooBars[0].Scalar;
    foo_bar_color += FooBars[1].Texture[1][int2(0,0)] * FooBars[1].Scalar;
    foo_bar_color += FooBars[2].Texture[2][int2(0,0)] * FooBars[2].Scalar;
    foo_bar_color += FooBars[3].Texture[3][int2(0,0)] * FooBars[3].Scalar;

    return foo_bar_color;
}
