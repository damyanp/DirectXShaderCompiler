// #4415 POSITIVE / ANTI-VACUITY CONTROL for match.json clause 2.
//
// match.json reads the ABSENCE of a validation failure as the symptom. That is
// only a measurement if a validation failure could have appeared in the same
// capture, through the same driver path, with no -Fo and no dxv. This case is
// adapted from the DXC test suite's own
// tools/clang/test/DXILValidation/rootSigDefine10.hlsl, whose RUN line is
//
//   RUN: %dxc -E main -T ps_6_0 -rootsig-define RS %s | FileCheck %s
//   CHECK: error: validation errors
//   CHECK: Root Signature in DXIL container is not compatible with shader
//
// The root signature declares an SRV descriptor table at t0 while the shader
// binds tex at t3, which DXIL validation rejects.
//
// Expected: `error: validation errors` on stderr and exit E_FAIL 0x80004005 --
// an ordinary diagnosed error, NOT an internal failure (SKILL.md exit table).
// Scored against match.json it must be no-match.

#define RS DescriptorTable(SRV(t0))

Texture1D<float> tex : register(t3);

float main(float i : I) : SV_Target {
  return tex[i];
}
