// Feature-presence control for #4605: the reporter's shader with the buffer
// declared RWByteAddressBuffer instead of RasterizerOrderedByteAddressBuffer.
// Differs from repro.hlsl in exactly one token. Must compile cleanly; if it
// does not, that build cannot answer the question the issue asks and its
// probe of repro.hlsl is not evidence.
RWByteAddressBuffer buf;
float4 main(uint idx1 : IDX1) : SV_Target {
  return buf.Load<float4>(idx1);
}
