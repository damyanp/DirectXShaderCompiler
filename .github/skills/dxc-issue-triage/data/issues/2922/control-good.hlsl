// Control for match.json: an ordinary shader that compiles cleanly and has no
// amplification payload and no pointer-typed dbg.value. Must NOT match.
float4 main(float4 c : COLOR) : SV_Target
{
    float4 v = c * 2.0f;
    return v;
}
