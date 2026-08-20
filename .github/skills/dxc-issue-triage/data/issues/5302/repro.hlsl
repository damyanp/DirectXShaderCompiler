// From issue #5302 (verbatim, with the reporter's own compile lines kept as comments):
// dxc /Tps_6_0 .\break.hlsl /DOUTPUT=SV_Target
// dxc /Tvs_6_0 .\break.hlsl /DOUTPUT=Z
StructuredBuffer<int> mainBuf[]: register(t2, space0);

[RootSignature("DescriptorTable(SRV(t2, numDescriptors=UNBOUNDED))")]
int main(int a : A, int b : B, int c : C) : OUTPUT
{
  int res = 0;

  for (;;) {
      int u = WaveReadLaneFirst(a);
      if (a == u) {
          res += mainBuf[u][b];
          break;
        }
    }
  return res;
}
