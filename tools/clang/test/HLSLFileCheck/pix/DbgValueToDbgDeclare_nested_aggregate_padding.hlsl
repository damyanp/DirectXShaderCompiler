// RUN: %dxc -Tcs_6_6 -Emain /Od /Zi %s | %opt -S -dxil-dbg-value-to-dbg-declare | %FileCheck %s

// Three levels of nesting, with tail padding at two of them. Each level's shortfall
// adds to the one below it, so the error grows the deeper the aggregate goes:
//
//   Leaf   is 128 bits (double + float + 32 bits of tail padding)
//   Middle is 192 bits (Leaf + float, no padding of its own)
//   Root   is 256 bits (Middle + float)
//
// so the declared offsets are 0, 64, 128 and 192. Summing member sizes instead
// reaches 0, 64, 96 and 128 - which is worse than dropping the last member, because
// AfterNested's value at declared bit 128 then resolves to the storage that was
// emitted for Trailing and PIX shows one member's value under another's name.

RWByteAddressBuffer RawUAV : register(u0);

struct Leaf
{
    double Wide;
    float Narrow;
};

struct Middle
{
    Leaf Nested;
    float AfterNested;
};

struct Root
{
    Middle Inner;
    float Trailing;
};

// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 0, 64)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 64, 32)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 128, 32)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 192, 32)

// CHECK: store double
// CHECK: store float
// CHECK: store float
// CHECK: store float

[numthreads(1, 1, 1)]
void main()
{
    Root root;
    root.Inner.Nested.Wide = (double)RawUAV.Load(2 * 4);
    root.Inner.Nested.Narrow = (float)RawUAV.Load(3 * 4);
    root.Inner.AfterNested = (float)RawUAV.Load(4 * 4);
    root.Trailing = (float)RawUAV.Load(5 * 4);

    RawUAV.Store(0, (float)root.Inner.Nested.Wide + root.Inner.Nested.Narrow +
                        root.Inner.AfterNested + root.Trailing);
}
