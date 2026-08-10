// Repro for issue 3863: the `-P` arm.
//
// Includes a header which itself includes a nested header, so the include
// trace `-H` would print has two entries and a non-zero stack depth. The
// header names here (inc-pp-a.h, inc-pp-b.h) are used ONLY by this shader, so
// an `Opening file [...]` line naming either of them can only have come from
// this arm of the run.
#include "inc-pp-a.h"

float4 main() : SV_Target {
  return ppmarker3863 + ppnested3863;
}
