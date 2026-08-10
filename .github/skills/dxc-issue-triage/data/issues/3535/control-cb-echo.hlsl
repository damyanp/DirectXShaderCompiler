// Issue 3535 control: the SAME identifiers the repro asks about, reached
// through the constant-buffer path instead of the input signature.
//
// Purpose: prove the absence clauses of match.json are live. `mPos` and
// `mColor` here are fields of a struct in a constant buffer, so reflection
// carries them and dxc prints them; the predicate must therefore score
// no-match. Run with `--expect no-match`.
//
// The input struct keeps the reporter's semantics (POSITION, COLOR) so the
// positive anchor still fires, and keeps cbAlpha so the self-test clause still
// fires -- only clauses 3 and 4 are meant to change.

struct VertexIn {
  float3 inA : POSITION;
  float3 inB : COLOR;
};

struct VertexOut {
  float4 oPosH : SV_Position;
  float3 oColor : COLOR;
};

struct CbStruct {
  float3 cbAlpha;
  float3 cbBeta;
};

struct CbEcho {
  float3 mPos;
  float3 mColor;
};

cbuffer Params : register(b0) {
  CbStruct gParams;
  CbEcho gEcho;
}

VertexOut VS(VertexIn vin) {
  VertexOut vout;
  vout.oPosH = float4(vin.inA + gParams.cbAlpha + gEcho.mPos, 1.0f);
  vout.oColor = vin.inB * gParams.cbBeta * gEcho.mColor;
  return vout;
}
