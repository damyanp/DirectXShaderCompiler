// #4723 repro source. The issue is about depfile generation, and a depfile is
// only interesting when the translation unit actually has dependencies, so this
// pulls in two headers, one of them nested.
#include "inc/common.hlsli"

float4 main(float4 pos : SV_Position) : SV_Target {
  return Tint(pos);
}
