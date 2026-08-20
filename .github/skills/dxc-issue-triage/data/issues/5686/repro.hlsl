struct payloadStruct
{
    uint myArbitraryData;
};

groupshared payloadStruct p;

[shader("amplification")]
[RootSignature("")]
[numthreads(1,1,1)]
void main(in uint3 groupID : SV_GroupID)
{
    p.myArbitraryData = groupID.z;
    DispatchMesh(1,1,1,p);
}
