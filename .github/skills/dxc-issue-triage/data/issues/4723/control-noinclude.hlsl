// #4723 control: the same shader with no #include at all.
//
// It exists to check that the finding is a property of -P and not of this
// repro's include layout -- a depfile whose only prerequisite is the source
// itself is still a depfile, and it is still not written under -P.
float4 main(float4 pos : SV_Position) : SV_Target {
  return pos * 0.5;
}
