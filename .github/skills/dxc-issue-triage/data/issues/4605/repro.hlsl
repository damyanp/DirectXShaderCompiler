// RUN: %dxc -T ps_6_0 %s | FileCheck %s
RasterizerOrderedByteAddressBuffer buf;
float4 main(uint idx1 : IDX1) : SV_Target {
  return buf.Load<float4>(idx1);
}
