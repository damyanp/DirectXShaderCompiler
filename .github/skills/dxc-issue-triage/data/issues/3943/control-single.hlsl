// #3943 negative control -- one include of the `#pragma once` header, spelled
// once. Nothing can be redefined, so the predicate must not fire.
// Expected: no-match. This is what proves the predicate discriminates rather
// than matching every compile of this header.
#include "inc/common.h"

float4 main() : SV_Target { return CommonValue(); }
