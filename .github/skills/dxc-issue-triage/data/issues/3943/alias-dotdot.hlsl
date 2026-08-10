// #3943 claim B -- the reporter's literal spelling, `Root/../MyFile.h`: a path
// containing a `..` component that cancels out. Both lines name the same file
// and both resolve relative to this file's own directory, so the -I search path
// plays no part here; only the spelling differs.
//
// No new directory is needed for this: `inc/..` traverses back out of a
// directory that already exists and is tracked by git.
#include "inc/common.h"
#include "inc/../inc/common.h"

float4 main() : SV_Target { return CommonValue(); }
