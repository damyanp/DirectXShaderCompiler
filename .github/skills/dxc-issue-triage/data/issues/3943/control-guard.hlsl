// #3943 control -- the same two spellings as repro.hlsl (relative to this file,
// then through -I inc), but the header uses a traditional `#ifndef` guard.
// A guard is keyed on a macro, not on file identity, so this must compile.
// Expected: no-match. If it matched, the defect would be far wider than the
// issue claims and the thread's workaround would not work either.
#include "inc/guarded.h"
#include "guarded.h"

float4 main() : SV_Target { return CommonValue(); }
