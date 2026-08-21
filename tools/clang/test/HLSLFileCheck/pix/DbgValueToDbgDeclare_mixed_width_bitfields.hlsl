// RUN: %dxc -Tcs_6_6 -Emain /Od /Zi %s | %opt -S -dxil-dbg-value-to-dbg-declare | %FileCheck %s

// Bitfields of differing widths.
//
// A bitfield deliberately suppresses alignment - DescendTypeToGetAlignMask returns 0
// for one - so nothing ever moved the walk's offset to where a bitfield member's
// debug info says it lives; the offset was just the running sum of the preceding
// members' widths. That sum is the declared offset only while the bitfields tile
// their storage unit exactly, and these do not: Leading and Trailing are 32-bit
// bitfields while Middle is a 64-bit one, so each opens its own unit and dxcompiler
// declares the three at bits 0, 64 and 128 while the walk produced 0, 5 and 64.
//
// The consequences were two different flavours of silently wrong:
//
//   Leading  declared at   0 -> its own 32-bit storage. Fine.
//   Middle   declared at  64 -> Trailing's 32-bit storage, but the value is 64-bit,
//                               so the width check rejected the store - and the
//                               dbg.value was erased regardless.
//   Trailing declared at 128 -> no storage at that offset at all, so its lookup
//                               missed outright.
//
// Note what the fix must be: the offsets have to come out right. Reconciling the
// width mismatch with a trunc or an ext instead would store Middle's value into
// Trailing's storage, which is a different member.

RWByteAddressBuffer RawUAV : register(u0);

struct MixedWidthBitfield
{
    uint32_t Leading : 5;
    uint64_t Middle : 59;
    uint32_t Trailing : 5;
};

// Each member's storage is declared at the bit offset its debug info gives it, and
// keeps its own declared width:
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 0, 5)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 64, 59)
// CHECK: dbg.declare{{.*}}!DIExpression(DW_OP_bit_piece, 128, 5)

// All three members are written. The 64-bit store is the one the width check used
// to reject, and it must be a plain i64 store into i64 storage - a truncation here
// would mean the offsets are still wrong.
// CHECK: store i32 %{{[0-9]+}}, i32*
// CHECK: store i64 %{{[0-9]+}}, i64*
// CHECK: store i32 %{{[0-9]+}}, i32*

[numthreads(1, 1, 1)]
void main()
{
    MixedWidthBitfield bitfield;
    bitfield.Leading = RawUAV.Load(9 * 4);
    bitfield.Middle = RawUAV.Load(21 * 4);
    bitfield.Trailing = RawUAV.Load(13 * 4);

    RawUAV.Store(0, (uint)(bitfield.Leading + bitfield.Middle + bitfield.Trailing));
}
