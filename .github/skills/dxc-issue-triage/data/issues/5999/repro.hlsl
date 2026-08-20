globallycoherent RWByteAddressBuffer   SomeBuffer;

template<typename BufferType>
uint TemplateFunction(BufferType AutoParam)
{
    return AutoParam.Load(0);
}

uint ExplicitFunction(globallycoherent RWByteAddressBuffer CoherentBuffer)
{
    return CoherentBuffer.Load(0);
}

[numthreads(1, 1, 1)]
void main()
{
    ExplicitFunction(SomeBuffer);
    TemplateFunction(SomeBuffer);
}
