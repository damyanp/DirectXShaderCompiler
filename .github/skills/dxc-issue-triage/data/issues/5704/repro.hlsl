Texture2D<uint> texResource : register(t900);
RWTexture2D<uint> rwTexResource[] : register(u0, space2400);
[numthreads(8, 8, 1)]
void main(uint3 dtid : SV_DispatchThreadID, uint3 gtid : SV_GroupThreadID, uint3 gid : SV_GroupID, uint gindex : SV_GroupIndex)
{
    rwTexResource[0][dtid.xy] = texResource.Load(dtid.xyz);
}