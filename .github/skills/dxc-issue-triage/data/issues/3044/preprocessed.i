#line 1 "repro.hlsl"





static const int selftest3044 = 1;
static const int macroexpanded3044 = 2;

float4 main() : SV_Target {

  return selftest3044 + macroexpanded3044;
}
