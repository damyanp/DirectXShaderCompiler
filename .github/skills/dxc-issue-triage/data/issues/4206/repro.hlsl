#define PROBE_COUNT 6
#define PROBE_VOLUME_SIZE 32

struct FProbeUpdateData
{
	uint3 Coord;
};
float4 WorldPosToProbeCoord[PROBE_COUNT];
float4 ProbeCoordToWorldPos[PROBE_COUNT];
RWBuffer<uint> RWProbeUpdateAllocator;
RWBuffer<uint> RWProbeUpdateBuffer;
RWBuffer<uint> RWProbeLightingBuffer;
float4 SkyLightColor;

FProbeUpdateData DecodeProbeUpdateData(uint2 ProbeDataEncoded)
{
	FProbeUpdateData ProbeData;
	ProbeData.Coord.x = ProbeDataEncoded.x & 0xFF;
	ProbeData.Coord.y = (ProbeDataEncoded.x >> 8) & 0xFF;
	ProbeData.Coord.z = (ProbeDataEncoded.x >> 16) & 0xFF;
    return ProbeData;
}

int3 WorldPosToProbeCoordInternal(float3 WorldPos, uint index)
{
	return floor(WorldPos * WorldPosToProbeCoord[index].w + WorldPosToProbeCoord[index].xyz);
}

uint3 WorldPosToProbeCoordIndex(float3 WorldPos, uint index)
{
	int3 ProbeCoord;
	ProbeCoord = WorldPosToProbeCoordInternal(WorldPos, index);
	ProbeCoord.x += index * PROBE_VOLUME_SIZE;
	return ProbeCoord;
}

float3 ProbeCoordToWorldPosCoord(uint3 ProbeCoord)
{
	uint index = ProbeCoord.x / PROBE_VOLUME_SIZE;
	ProbeCoord.x -= index * PROBE_VOLUME_SIZE;
	return (float3)ProbeCoord * ProbeCoordToWorldPos[index].w + ProbeCoordToWorldPos[index].xyz;
}

[numthreads(64, 1, 1)]
void ResampleCS(uint3 DispatchThreadID : SV_DispatchThreadID, uint3 GroupID : SV_GroupID)
{
	uint NewProbeID = DispatchThreadID.x;
	uint ProbeUpdateIndex = RWProbeUpdateAllocator[0] + NewProbeID;
	uint2 ProbeDataEncoded;
	ProbeDataEncoded.x = RWProbeUpdateBuffer[ProbeUpdateIndex * 2];
	ProbeDataEncoded.y = RWProbeUpdateBuffer[ProbeUpdateIndex * 2 + 1];
	FProbeUpdateData ProbeData = DecodeProbeUpdateData(ProbeDataEncoded);

        float3 ProbePos = ProbeCoordToWorldPosCoord(ProbeData.Coord);
	uint ProbeIndex = ProbeData.Coord.x / PROBE_VOLUME_SIZE;

    uint3 SourceProbeCoord = WorldPosToProbeCoordIndex(ProbePos + 0.5f, ProbeIndex - 1);
    RWProbeLightingBuffer[SourceProbeCoord.x] = SourceProbeCoord.y;
}
