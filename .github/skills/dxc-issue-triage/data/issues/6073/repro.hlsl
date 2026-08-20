template<int ID>
struct Test
{
    static int Num;
};

template<int ID>
int Test<ID>::Num = 2;

RWBuffer<int> MyBuffer;

[numthreads(1,1,1)]
void main(uint3 DispatchThreadId : SV_DispatchThreadID)
{
   MyBuffer[DispatchThreadId.x] = Test<42>::Num;
}
