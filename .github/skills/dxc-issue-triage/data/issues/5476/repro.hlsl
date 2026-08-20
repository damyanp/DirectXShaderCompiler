StructuredBuffer<matrix> buf1;
RWBuffer<float4> buf2;

[RootSignature("DescriptorTable(SRV(t0), UAV(u0))")]
[numthreads(8, 8, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  buf2[tid.x] = buf1[tid.x][tid.y];
}
