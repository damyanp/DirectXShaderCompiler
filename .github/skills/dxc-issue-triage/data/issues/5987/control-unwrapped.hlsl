// Reporter's other negative control: "unwrap" the struct so payloadType's
// members are loose scalars/arrays instead of a nested struct, then assign
// each member individually. Reporter says this avoids the error.
struct payloadType {
	float4x4 mat;
	int array[3];
	float2 vec;
};

groupshared payloadType payload;

[numthreads(1, 1, 1)]
void main()
{
	payload.mat = (float4x4)0;
	payload.array[0] = 0;
	payload.array[1] = 0;
	payload.array[2] = 0;
	payload.vec = (float2)0;

	DispatchMesh(1, 1, 1, payload);
}
