struct S {
     uint v;
};

StructuredBuffer<S> stbuf;

uint main() : OUT
{
     int j;
     return stbuf[j].v;
}
