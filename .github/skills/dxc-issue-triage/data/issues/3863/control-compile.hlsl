// Control for issue 3863: the `-H`-on-a-normal-compile arm.
//
// Identical in shape to repro.hlsl, but includes differently named headers, so
// the `Opening file [...]` lines it produces cannot be confused with the `-P`
// arm's. This is the in-predicate self-test: if -H ever stops working at all,
// this clause fails and the probe scores no-match instead of manufacturing a
// clean absence for the -P arm.
#include "inc-comp-a.h"

float4 main() : SV_Target {
  return compmarker3863 + compnested3863;
}
