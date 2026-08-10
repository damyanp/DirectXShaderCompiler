// Control for #3835 that exercises the exact confusion in the issue's title:
// "Internal compiler error on shader validation". This shader compiles, then
// **DXIL validation** rejects it (duplicate LOC0 input semantic), which is the
// pattern of tools/clang/test/HLSLFileCheck/hlsl/diagnostics/errors/
// semantics_duplicate_struct_error.hlsl. dxc exits E_FAIL (0x80004005) -- the
// same nonzero status the repro's *internal* failure would be confused with if
// the predicate were "nonzero exit". Must score no-match: the validator doing
// its job is not an internal compiler error.
struct VertexInput {
    float2 a_uv2 : LOC0;
    float2 a_pos2 : LOC0;
};

float4 vert_main(VertexInput vertexinput) : SV_Position
{
    return float4(vertexinput.a_uv2 + vertexinput.a_pos2, 0.0, 1.0);
}
