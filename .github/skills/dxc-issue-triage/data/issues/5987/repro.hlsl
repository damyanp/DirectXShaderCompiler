struct s {
	float4x4 mat;
	int array[3];
	float2 vec;
};

struct payloadType { s data; };

groupshared payloadType payload;

[numthreads(1, 1, 1)]
void main()
{
	s blah = (s)0;
	payload.data = blah;

	DispatchMesh(1, 1, 1, payload);
}
