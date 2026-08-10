#line 1 "repro.hlsl"







#line 1 "./inc-pp-a.h"

#line 1 "./inc-pp-b.h"

static const int ppnested3863 = 2;
#line 2 "./inc-pp-a.h"

static const int ppmarker3863 = 1;
#line 8 "repro.hlsl"


float4 main() : SV_Target {
  return ppmarker3863 + ppnested3863;
}
