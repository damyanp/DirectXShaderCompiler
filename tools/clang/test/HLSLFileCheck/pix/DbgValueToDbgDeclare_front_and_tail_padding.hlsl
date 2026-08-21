// RUN: %dxc -Tcs_6_6 -Emain /Od /Zi %s | %opt -S -dxil-dbg-value-to-dbg-declare | %FileCheck %s

// Padding in front of a member versus padding at the end of an aggregate.
//
// FrontPadded's padding sits between its two members, and the walk has always got
// that right: aligning in front of Wide skips it. This half of the test is the
// regression guard - skipping to the end of an aggregate must not disturb the
// aggregates that were already laid out correctly.
//
// TailPadded's padding sits after its last member, where there is no following
// member whose alignment could skip it, and that is the case that was broken.
// Trailing is declared at bit 256; summing member sizes reaches only bit 224.

RWByteAddressBuffer RawUAV : register(u0);

struct FrontPadded
{
    float Narrow;
    double Wide;
};

struct TailPadded
{
    double Wide;
    float Narrow;
};

struct Holder
{
    FrontPadded Front;
    TailPadded Tail;
    float Trailing;
};

// The front-padded aggregate: Wide is at bit 64, not at bit 32, both before and
// after the fix.
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 0, 32)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 64, 64)
// The tail-padded aggregate starts at bit 128:
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 128, 64)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 192, 32)
// And the member after it must land on bit 256, not on bit 224:
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 256, 32)

// CHECK: store float
// CHECK: store double
// CHECK: store double
// CHECK: store float
// CHECK: store float

[numthreads(1, 1, 1)]
void main()
{
    Holder holder;
    holder.Front.Narrow = (float)RawUAV.Load(2 * 4);
    holder.Front.Wide = (double)RawUAV.Load(3 * 4);
    holder.Tail.Wide = (double)RawUAV.Load(4 * 4);
    holder.Tail.Narrow = (float)RawUAV.Load(5 * 4);
    holder.Trailing = (float)RawUAV.Load(6 * 4);

    RawUAV.Store(0, holder.Front.Narrow + (float)holder.Front.Wide +
                        (float)holder.Tail.Wide + holder.Tail.Narrow + holder.Trailing);
}
