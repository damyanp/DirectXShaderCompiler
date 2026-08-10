// #3943 -- one header, reached by two different spellings of its path.
//
//   "inc/common.h"  resolves relative to this file's own directory
//   "common.h"      resolves through the -I inc search path
//
// Both name the same physical file. `#pragma once` in that file should suppress
// the second inclusion. The issue reports that it does not, so CommonValue()
// gets defined twice.
#include "inc/common.h"
#include "common.h"

float4 main() : SV_Target { return CommonValue(); }
