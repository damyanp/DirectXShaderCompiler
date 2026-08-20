void f(unsigned int){}
void f(int){}

float4 PSMain() : SV_TARGET
{
    f(1);
    return (float4)0;
}
