// Control for the Clang pane of the discriminating case.
//
// case-cstyle-cast.hlsl needs an RWBuffer to make the chosen conversion
// observable. Clang's HLSL backend is incomplete, so a failure there could be
// about the resource rather than about the operator. This is the same shader
// with the struct and the cast removed: if THIS fails too, the resource is the
// blocker and the discriminating pane says nothing about conversions.
RWBuffer<uint> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
  Out[tidx] = 111;
}
