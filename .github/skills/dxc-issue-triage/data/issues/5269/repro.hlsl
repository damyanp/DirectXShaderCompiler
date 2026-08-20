struct Payload
{
};

[numthreads(32, 1, 1)]
void main()
{
    Payload pld;
    DispatchMesh(32, 1, 1, pld);
}
