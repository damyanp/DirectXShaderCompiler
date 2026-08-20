// Control: uses ResourceDescriptorHeap and a statically-registered resource of the same
// type, but WITHOUT reassigning the static variable to the dynamic handle and without using
// the static resource before the dynamic one is created. Proves the defect is specific to
// the "use static resource, then reassign it to a dynamic handle, then use it again"
// pattern -- not to ResourceDescriptorHeap or a mixed static/dynamic shader in general.
RWByteAddressBuffer buffer : register(u0);

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
        RWByteAddressBuffer dynBuffer = ResourceDescriptorHeap[0];
        dynBuffer.Store(id.x, 0);
        buffer.Store(id.x, 1);
}
