// Issue 3535, the reporter's shader with nothing added: no constant buffer,
// therefore no in-run self-test. Kept so the exact configuration in the issue
// body is on disk and re-runnable.
//
// VertexIn is verbatim from the issue. VertexOut and the entry body are
// supplied because the issue elides them ("layout unimportant to question").

struct VertexIn {
  float3 mPos : POSITION;
  float3 mColor : COLOR;
};

struct VertexOut {
  float4 oPosH : SV_Position;
  float3 oColor : COLOR;
};

VertexOut VS(VertexIn vin) {
  VertexOut vout;
  vout.oPosH = float4(vin.mPos, 1.0f);
  vout.oColor = vin.mColor;
  return vout;
}
