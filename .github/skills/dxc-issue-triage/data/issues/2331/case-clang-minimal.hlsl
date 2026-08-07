// Not the issue's repro, and not published.  A cut-down restating that clang's DXIL backend
// can actually compile (no ConstantBuffer<T>), used only to ask one supplementary question:
// does clang still emit an LLVM `unreachable` for the fall-off-the-end path of an
// exhaustive enum switch?  @llvm-beanz said in 2024 he had filed an issue to remove these
// during DXIL lowering in clang.  See manual-case-clang.txt.
enum class QualityT { Low, Medium, High, };
RWBuffer<float4> Out : register(u0);

float4 Shade(QualityT q)
{
switch ( q )
{
    case QualityT::Low:    return float4 (4, 0, 0, 0) ;
    case QualityT::Medium: return float4 (0, 4, 0, 0) ;
    case QualityT::High:   return float4 (0, 0, 4, 0) ;
} 
}

[numthreads(1, 1, 1)]
void MainCS(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x] = Shade((QualityT)(tid.x & 3));
}
