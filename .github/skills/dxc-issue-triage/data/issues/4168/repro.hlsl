// #4168 repro -- cbuffer variables of a LINKED shader.
//
// The reporter's configuration, from the 2022-01-23 comment: "compile modules
// in lib_6_x profile, and link to ps_6_0".
//
// lib_6_x is what makes this direction interesting. Its minor version is
// kOfflineMinor = 0xF (include/dxc/DXIL/DxilShaderModel.h:47), so the library
// is shader model 6.15 and IsSM66Plus() is true for it: the library gets
// DxilMutateResourceToHandle run over it and the cbuffer global is rewritten to
// dx.types.Handle. The link target ps_6_0 is below 6.6 and has no mutation.
// That mismatch is what the reporter's two "problems" are about.
//
// CB0 has two members so that a reflected "Num Variables: 0" is distinguishable
// from a cbuffer that genuinely has no members.

cbuffer CB0 {
  row_major float4x4 m;
  float4 f;
}

export float4 xform(float4 v) {
  return mul(v, m);
}

[shader("pixel")]
float4 main(float4 pos : TEXCOORD0) : SV_Target {
  return xform(pos) * f;
}
