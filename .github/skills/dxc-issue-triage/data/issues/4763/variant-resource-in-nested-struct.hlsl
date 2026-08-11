// Variant for issue 4763: tests the specific claim in
// https://github.com/microsoft/DirectXShaderCompiler/issues/4763#issuecomment-1650593899
// that a resource placed in a struct, which is then used as a *field*, leaves the
// following field 16-byte aligned even though the resource itself occupies 0 size.
// This is a different construct from repro.hlsl, where the resource is a direct member.
//
// Three cbuffers, read together:
//   cbNested    - inner struct holds a Texture2D (a genuinely 0-size resource)
//   cbNestedSB  - inner struct holds a StructuredBuffer<float3> (the issue's case)
//   cbControl   - identical shape with no inner struct at all; 'next' should sit at 4
// Comparing 'next' across the three separates an alignment effect from a size effect.

struct InnerTex { Texture2D t; };
struct InnerSB { StructuredBuffer<float3> b; };

struct OuterTex {
    uint a;
    InnerTex inner;
    uint next;
};

struct OuterSB {
    uint a;
    InnerSB inner;
    uint next;
};

struct Control {
    uint a;
    uint next;
};

ConstantBuffer<OuterTex> cbNested;
ConstantBuffer<OuterSB> cbNestedSB;
ConstantBuffer<Control> cbControl;

float4 PSMain() : SV_Target {
    return cbNested.a + cbNested.next + cbNestedSB.a + cbNestedSB.next +
           cbControl.a + cbControl.next;
}
