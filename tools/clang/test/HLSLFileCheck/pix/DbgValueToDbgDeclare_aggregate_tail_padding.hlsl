// RUN: %dxc -Tcs_6_6 -Emain /Od /Zi %s | %opt -S -dxil-dbg-value-to-dbg-declare | %FileCheck %s

// A struct whose alignment forces tail padding, used as a non-final member.
//
// TailPadded is 128 bits wide, not 96: the double aligns it to 64 bits, so Narrow
// occupies bits 64-95 and bits 96-127 are tail padding. The debug info therefore
// describes Trailing at bit 128, and that is the offset dxcompiler puts in
// Trailing's llvm.dbg.value.
//
// The pass used to advance its running offset by the sum of the members' sizes
// rather than by the aggregate's own size, so it reached only bit 96 and emitted
// Trailing's shadow storage there. handleDbgValue then looked Trailing up at the
// declared bit 128, found nothing, skipped its store, and erased the dbg.value
// anyway - leaving PIX with a register it believes is live that nothing ever wrote.

RWByteAddressBuffer RawUAV : register(u0);

struct TailPadded
{
    double Wide;
    float Narrow;
};

struct Holder
{
    TailPadded Padded;
    float Trailing;
};

// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 0, 64)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 64, 32)
// The member after the padded aggregate must land on bit 128, not on bit 96:
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 128, 32)

// All three members must be written to their shadow storage. Trailing's store is
// the one that goes missing when its lookup fails.
// CHECK: store double
// CHECK: store float
// CHECK: store float

[numthreads(1, 1, 1)]
void main()
{
    Holder holder;
    holder.Padded.Wide = (double)RawUAV.Load(2 * 4);
    holder.Padded.Narrow = (float)RawUAV.Load(3 * 4);
    holder.Trailing = (float)RawUAV.Load(7 * 4);

    RawUAV.Store(0, (float)holder.Padded.Wide + holder.Padded.Narrow + holder.Trailing);
}
