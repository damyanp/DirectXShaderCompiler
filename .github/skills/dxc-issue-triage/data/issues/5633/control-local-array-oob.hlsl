// Control: local (non-resource) fixed-size array indexed with an out-of-bounds
// compile-time constant literal. This asks whether DXC already implements *any*
// form of the requested static-bounds diagnostic outside of structured-buffer
// members, so the primary repro's silence is not attributed to a gap that
// turns out to be universal.
float4 main() : SV_TARGET
{
    float arr[1];
    arr[0] = 1.0f;
    return arr[2000].xxxx;
}
