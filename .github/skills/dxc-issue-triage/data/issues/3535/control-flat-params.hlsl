// Issue 3535 identity control: the same entry point written with flat,
// individually named parameters instead of a struct.
//
// Purpose: show the finding is not specific to struct members. If the HLSL
// identifier is lost here too, the request is "reflection does not record the
// source-level name of a signature element", of which the reporter's struct
// case is one instance. Run with `--expect match`.

struct VertexOut {
  float4 oPosH : SV_Position;
  float3 oColor : COLOR;
};

struct CbStruct {
  float3 cbAlpha;
  float3 cbBeta;
};

cbuffer Params : register(b0) { CbStruct gParams; }

VertexOut VS(float3 mPos : POSITION, float3 mColor : COLOR) {
  VertexOut vout;
  vout.oPosH = float4(mPos + gParams.cbAlpha, 1.0f);
  vout.oColor = mColor * gParams.cbBeta;
  return vout;
}
