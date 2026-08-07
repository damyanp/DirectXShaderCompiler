// Methodology probe, not a probe of #3055's repro. See method-notes.md.
//
// `clamp` is an intrinsic and it is obviously declared, but no overload takes
// four arguments. dxc's answer is `error: use of undeclared identifier
// 'clamp'` -- a plausible diagnostic-quality bug of exactly the class #3055 is
// about, and one someone could reasonably file.
//
// It is here because that message is verbatim one of the runner's
// unsupported-feature markers ("the compiler predates this feature and never
// reached the code under test"). A triager predicating on it measures what the
// classifier then does.

float4 main(float2 coord : C) : SV_Target {
  return clamp(coord, 1, 2, 3).xyxy;
}
