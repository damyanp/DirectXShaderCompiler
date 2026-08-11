// Feature-presence control for the Store half of #4605: identical to
// store-rov.hlsl but on RWByteAddressBuffer. Must compile cleanly.
RWByteAddressBuffer buf;
float4 main(uint idx1 : IDX1) : SV_Target {
  buf.Store<float4>(idx1, float4(1, 2, 3, 4));
  return 0;
}
