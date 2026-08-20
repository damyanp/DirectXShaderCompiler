[RootSignature("")]
float4 main(int a : A) : SV_Target {
  return (float4)(float)WaveReadLaneFirst(a);
}
