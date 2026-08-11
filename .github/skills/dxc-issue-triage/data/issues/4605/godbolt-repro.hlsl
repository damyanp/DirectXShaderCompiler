// Compiler Explorer publication of #4605's repro. CE gives every pane one
// shared source, so the contrasts are expressed as -D flags. The default arm
// is the reporter's shader verbatim; -DUSE_RW swaps only the buffer type;
// -DUNTEMPLATED keeps the rasterizer-ordered type and drops the template
// argument list. Every arm is measured locally before publishing
// (variant-godbolt-src*-main-debug.txt) so the transformation is not the
// subject.
#ifdef USE_RW
RWByteAddressBuffer buf;
#else
RasterizerOrderedByteAddressBuffer buf;
#endif

float4 main(uint idx1 : IDX1) : SV_Target {
#ifdef UNTEMPLATED
  return (float4)buf.Load(idx1);
#else
  return buf.Load<float4>(idx1);
#endif
}
