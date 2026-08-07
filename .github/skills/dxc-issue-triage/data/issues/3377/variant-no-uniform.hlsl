// Does the crash need the `uniform` keyword? variant-minimal.hlsl keeps it, as the report
// does; this drops it and changes nothing else.
//
// Also the only form of the construct Clang's HLSL front end can even parse -- it rejects
// `uniform` parameters outright with "unknown type name 'uniform'" (see
// manual-case-ce-clang.txt) -- so it is what a Clang comparison would have to use.
//
// Run with `--expect match`: this variant must fail exactly as the repro does, or the claim
// that `uniform` is irrelevant is not supported.

float4 main_fragment(Texture2D<float4> decal : TEXUNIT0) : SV_Target
{
	return decal.Load(int3(0, 0, 0));
}
