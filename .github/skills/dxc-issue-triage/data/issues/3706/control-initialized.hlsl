// Negative control for #3706: identical to repro.hlsl except that j IS initialized.
// The predicate must NOT match: the index operand becomes a constant, not undef.
struct S {
     uint v;
};

StructuredBuffer<S> stbuf;

uint main() : OUT
{
     int j = 0;
     return stbuf[j].v;
}
