// #3943 control -- the same two include *spellings* as repro.hlsl (one local,
// one through -I inc), except the local one uses a backslash separator.
//
// On Windows the -I search joins its directory to the file name with `\`, so
// this spelling makes both includes resolve to the byte-identical path string
// `./inc\common.h`, and `#pragma once` then works. repro.hlsl differs from this
// file in exactly one character.
//
// Expected: no-match. It is what shows the comparison is a literal comparison
// of the resolved path string rather than a comparison of file identity: change
// nothing about which file is opened, only how its path is spelled, and the
// behaviour flips.
#include "inc\common.h"
#include "common.h"

float4 main() : SV_Target { return CommonValue(); }
