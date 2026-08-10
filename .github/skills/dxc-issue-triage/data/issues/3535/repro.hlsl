// Issue 3535 repro. The reporter's shader, completed, plus one deliberate
// addition described below.
//
// As filed (verbatim from the issue body):
//
//     struct VertexIn
//     {
//         float3 mPos : POSITION;
//         float3 mColor : COLOR;
//     };
//     struct VertexOut;  // layout unimportant to question
//
//     VertexOut VS(VertexIn vin)
//     {
//         // some math here, return a VertexOut
//     }
//
// VertexIn is verbatim. VertexOut and the body are supplied because the issue
// elides them and calls their layout unimportant; the output members are named
// oPosH/oColor so that no output identifier is a substring of an input one.
//
// The constant buffer is the deliberate addition. It is the in-run self-test:
// the same reflection walk that is asked for the input struct's member names is
// asked for a constant-buffer struct's member names in the same container, so a
// run that reports "no member names" because the instrument stopped working
// scores no-match instead of manufacturing an absence. cbAlpha/cbBeta are
// distinct from every input identifier on purpose.
//
// repro-as-filed.hlsl is the reporter's shader without that addition.

struct VertexIn {
  float3 mPos : POSITION;
  float3 mColor : COLOR;
};

struct VertexOut {
  float4 oPosH : SV_Position;
  float3 oColor : COLOR;
};

struct CbStruct {
  float3 cbAlpha;
  float3 cbBeta;
};

cbuffer Params : register(b0) { CbStruct gParams; }

VertexOut VS(VertexIn vin) {
  VertexOut vout;
  vout.oPosH = float4(vin.mPos + gParams.cbAlpha, 1.0f);
  vout.oColor = vin.mColor * gParams.cbBeta;
  return vout;
}
