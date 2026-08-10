// Negative control for #3927's predicate.
//
// Identical to repro.hlsl except that the Tex0 sample and the branch it feeds are gone, so
// Tex0/SS0 are declared but genuinely unreferenced. DXC's SPIR-V dead-variable elimination
// does remove an unreferenced resource, so this shader must compile, emit
// `OpEntryPoint Fragment %main`, and carry NO `OpDecorate %Tex0 Binding`.
//
// This is what stops the predicate from being satisfied by "any successful -spirv compile of
// a shader that happens to declare Tex0". Expect: no-match.
struct PixelInput
{
	float4 pos : SV_Position0;
	float2 texCoord : TEXCOORD0;
};

Texture2D Tex0;
SamplerState SS0;
Texture2D Tex1;
SamplerState SS1;

float4 main(in PixelInput In) : SV_Target0
{
	return Tex1.Sample(SS1, In.texCoord);
}
