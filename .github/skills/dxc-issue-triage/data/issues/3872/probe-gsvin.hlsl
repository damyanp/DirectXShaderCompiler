// Issue 3872 -- the OPEN QUESTION arm, kept out of repro.hlsl on purpose.
//
// The report asserts four cells are wrong (HSCPIn, HSCPOut, DSCPIn, DSOut) and
// separately *asks* about a fifth: "GSVIn probably should be NA as well, but
// I'm not sure".  That is a question, not a claim, so it is measured here as a
// labelled variant rather than scored as part of the repro -- a predicate that
// mixes an assertion with a question cannot be falsified cleanly.
//
// GSVIn is the geometry shader's per-vertex INPUT signature, i.e. the element
// type of the GS entry point's input array.  The interpretation table gives
// GSVIn = SV _64 for ShadingRate, so this is expected to compile today; the
// point of the probe is to record what today's behaviour actually is so the
// question can be answered from evidence.
//
//   GSVInMain   gs_6_4   GSVIn   <- open question
//
// The shader deliberately does NOT write SV_ShadingRate on its output: GSOut
// is uncontested (the VRS spec permits setting the rate from a GS), and mixing
// the two would make the capture unreadable.

struct VSOutRate {
  float4 pos : SV_Position;
  uint rate : SV_ShadingRate;
};

struct GSOutPlain {
  float4 pos : SV_Position;
  float2 uv : TEXCOORD0;
};

[maxvertexcount(3)]
void GSVInMain(triangle VSOutRate ip[3], inout TriangleStream<GSOutPlain> os) {
  [unroll] for (uint i = 0; i < 3; ++i) {
    GSOutPlain o;
    o.pos = ip[i].pos;
    o.uv = (float2)ip[i].rate;
    os.Append(o);
  }
  os.RestartStrip();
}
