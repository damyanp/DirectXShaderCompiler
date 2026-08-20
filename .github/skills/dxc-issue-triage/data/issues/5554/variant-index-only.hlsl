// Isolates the array-index sub-question from the template-argument sub-question in Ask A:
// does `partiboi[KEK::WAIT]` (no cast) compile on its own, with no template involved at all?
enum class KEK : uint
{
NO = 0,
WAIT=69,
COUNT=70
};

RWStructuredBuffer<int> buf;

[numthreads(1,1,1)]
void main()
{
    int partiboi[128];
    for (int i = 0; i < 128; i++) partiboi[i] = i;
    buf[0] = partiboi[(uint)KEK::WAIT];
    buf[1] = partiboi[KEK::WAIT];
}
