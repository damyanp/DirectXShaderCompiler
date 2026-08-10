// Instrument self-test for #3943. Compiled as line 1 of cmd.txt on EVERY probe,
// including every release visited by `bisect` and every labelled variant.
//
// It includes the same header twice by the IDENTICAL spelling, so `#pragma once`
// must suppress the second inclusion and this must compile and emit DXIL. If it
// does not, that build cannot measure the repro at all -- the header was not
// reachable, or -I did not work, or `#pragma once` is broken outright -- and the
// probe is unmeasurable rather than clean. match.json therefore requires this
// compile's DXIL as a clause, so `reindex` re-checks it forever.
//
// The .hlsli extension is deliberate: `triage.py run --shader` rewrites only
// argv tokens ending in .hlsl, so this self-test line survives unchanged when a
// variant retargets the repro line. Renaming it to .hlsl would silently make
// every labelled variant overwrite its own self-test.
#include "inc/common.h"
#include "inc/common.h"

float4 main() : SV_Target { return CommonValue(); }
