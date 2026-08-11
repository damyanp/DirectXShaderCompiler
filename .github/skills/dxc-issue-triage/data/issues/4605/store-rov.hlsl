// The title's second half for #4605: templated Store on
// RasterizerOrderedByteAddressBuffer. Scored under match-store.json.
RasterizerOrderedByteAddressBuffer buf;
float4 main(uint idx1 : IDX1) : SV_Target {
  buf.Store<float4>(idx1, float4(1, 2, 3, 4));
  return 0;
}
