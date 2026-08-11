// Control for #4605: RasterizerOrderedByteAddressBuffer with the *untemplated*
// Load. Proves the ROV type itself is declarable and usable at ps_6_0, so a
// rejection of repro.hlsl is about the explicit template arguments and not
// about the resource type or the profile.
RasterizerOrderedByteAddressBuffer buf;
float4 main(uint idx1 : IDX1) : SV_Target {
  return (float4)buf.Load(idx1);
}
