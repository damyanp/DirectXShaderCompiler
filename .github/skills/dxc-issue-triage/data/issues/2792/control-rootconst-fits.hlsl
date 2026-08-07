// Identity control for #2792. Byte-for-byte the repro, except the root
// constant block is declared large enough (num32BitConstants = 2) to hold both
// floats -- so this shader is entirely correct and nothing is out of bounds.
//
// The finding is the *sameness*: DXC emits identical DXIL and identical
// (empty) diagnostics for this and for repro.hlsl, because num32BitConstants
// is never compared against the size of the cbuffer bound to that register.
// match.json therefore fires on this too, and that is the point -- see #1803
// for the same shape of control.  --expect match.
cbuffer cb : register(b0)
{
  float a;
  float b;
}

[RootSignature("RootFlags(0), RootConstants(b0, num32BitConstants = 2)")]
float main() : SV_Target {
  return b;
}
