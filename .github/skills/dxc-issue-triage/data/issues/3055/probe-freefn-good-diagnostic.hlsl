// Methodology probe, not a probe of #3055's repro. See method-notes.md.
//
// The FREE-FUNCTION sibling of #3055's defect: the same user mistake (passing a
// SamplerComparisonState where a different type is wanted), but to an intrinsic
// *function* rather than an intrinsic *method*. #2693 / #818 fixed reporting on
// this path, so dxc names the conversion that failed -- i.e. this is what
// #3055's diagnostic would look like if it were fixed.
//
// It exists to measure what the runner does with a probe whose output carries
// the string "no matching function for call to", which is one of the runner's
// unsupported-feature markers.

SamplerComparisonState samp;

float4 main(float2 coord : C) : SV_Target {
  return clamp(coord, samp, 1).xyxy;
}
