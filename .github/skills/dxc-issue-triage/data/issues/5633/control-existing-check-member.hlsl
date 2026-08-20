// Existing-diagnostic control (C): the out-of-bounds array is a struct
// member (`s.pad[2000]`) reached through a MemberExpr, but the result is
// still returned bare (no swizzle). This isolates whether accessing the
// array through a struct member -- as the reporter's repro does via
// `lineStyles[45]._pad[...]` -- silences DXC's existing bounds check on its
// own, independent of any swizzle.
struct S { float pad[1]; };

float4 main() : SV_TARGET
{
    S s;
    s.pad[0] = 0;
    return s.pad[2000];
}
