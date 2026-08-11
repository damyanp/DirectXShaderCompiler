// Instrument control for match-ignored-register.json. Same variable name, same
// register spelling as control-as-u0-alone.hlsl, but a genuinely UAV-class
// resource, for which register(u0) is correct.
//
// It proves two things the binding predicate would otherwise assume:
//   * the resource-binding table can print a `u0` bind at all, so the
//     not_regex clause is falsifiable rather than vacuous;
//   * the predicate keys on where the resource ended up, not on the name.

RWBuffer<float> opaque_as : register(u0);

float4 main(float4 pos : SV_Position) : SV_Target {
  return float4(opaque_as[0], 0, 0, 1);
}
