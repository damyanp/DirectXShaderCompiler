// Existing-diagnostic control (B): identical base case to
// control-existing-check-plain.hlsl, except the out-of-bounds element is
// swizzled (`.xxxx`) before being returned, exactly as the reporter's repro
// does (`float(lineStyles[45]._pad[2000]).xxxx`). This isolates whether a
// trailing swizzle alone is enough to silence DXC's existing bounds check,
// independent of any struct/buffer member access.
float4 main() : SV_TARGET
{
    float arr[1];
    return arr[2000].xxxx;
}
