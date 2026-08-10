// #3943 claim C, from otanter-at-ubi's comment: "it is also case sensitive".
// On Windows/NTFS these two spellings name one file, so `#pragma once` should
// suppress the second inclusion. On a case-sensitive filesystem they name two
// different paths and only one exists, so this case is meaningful ONLY on a
// case-insensitive filesystem; the ground truth here is Windows.
#include "inc/common.h"
#include "inc/COMMON.h"

float4 main() : SV_Target { return CommonValue(); }
