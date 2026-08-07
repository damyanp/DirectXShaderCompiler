// Minimisation variant for #3377, testing @damyanp's 2024-07-09 comment:
//
//   "Although the call stack above looks like it is going through matrix code, when looking
//    at more minimal repros of this matrices aren't involved. Main issue seems to be around
//    having a semantic set on a texture parameter to the entry point"
//
// No matrix anywhere, no effect-syntax SamplerState, no second entry point, no Sample(): just
// a Texture2D entry-point parameter carrying a semantic. Entry point name matches the repro so
// cmd.txt's arguments are reused unchanged.
//
// Expect: match. This is an identity-style control -- sameness with the repro IS the finding.

float4 main_fragment(uniform Texture2D<float4> decal : TEXUNIT0) : SV_Target
{
	return decal.Load(int3(0, 0, 0));
}
