// Control for #3835 proving an ordinary DIAGNOSED error does not score as an
// internal failure. dxc rejects this with an `error:` and exits E_FAIL
// (0x80004005) -- the same exit status a DXIL validation failure and an
// invalid profile use. The issue's title says "on shader validation", so the
// predicate must be able to tell that class apart from a real internal
// failure; this control is the measurement that it can. Must score no-match.
struct VertexInput {
    float2 a_pos2 : LOC0;
};

float4 vert_main(VertexInput vertexinput) : SV_Position
{
    return float4(vertexinput.a_pos2, 0.0, 1.0
}
