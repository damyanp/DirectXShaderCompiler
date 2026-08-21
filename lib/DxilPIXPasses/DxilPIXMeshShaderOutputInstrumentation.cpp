///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// DxilAddPixelHitInstrumentation.cpp                                        //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// Provides a pass to add instrumentation to retrieve mesh shader output.    //
// Used by PIX.                                                              //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include "dxc/DXIL/DxilOperations.h"
#include "dxc/DXIL/DxilUtil.h"

#include "dxc/DXIL/DxilConstants.h"
#include "dxc/DXIL/DxilInstructions.h"
#include "dxc/DXIL/DxilModule.h"
#include "dxc/DxilPIXPasses/DxilPIXPasses.h"
#include "dxc/HLSL/DxilGenerationPass.h"
#include "dxc/HLSL/DxilSpanAllocator.h"

#include "llvm/IR/InstIterator.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Support/FormattedStream.h"
#include "llvm/Transforms/Utils/Local.h"
#include <deque>

#ifdef _WIN32
#include <winerror.h>
#endif

#include "PixPassHelpers.h"

// Keep these in sync with the same-named value in the debugger application's
// WinPixShaderUtils.h

constexpr uint64_t DebugBufferDumpingGroundSize = 64 * 1024;
// The actual max size per record is much smaller than this, but it never
// hurts to be generous.
constexpr size_t CounterOffsetBeyondUsefulData =
    DebugBufferDumpingGroundSize / 2;

// Keep these in sync with the same-named values in PIX's MeshShaderOutput.cpp
constexpr uint32_t triangleIndexIndicator = 0x1;
constexpr uint32_t int32ValueIndicator = 0x2;
constexpr uint32_t floatValueIndicator = 0x3;
constexpr uint32_t int16ValueIndicator = 0x4;
constexpr uint32_t float16ValueIndicator = 0x5;

using namespace llvm;
using namespace hlsl;
using namespace PIXPassHelpers;

class DxilPIXMeshShaderOutputInstrumentation : public ModulePass {
public:
  static char ID; // Pass identification, replacement for typeid
  explicit DxilPIXMeshShaderOutputInstrumentation() : ModulePass(ID) {}
  StringRef getPassName() const override {
    return "DXIL mesh shader output instrumentation";
  }
  void applyOptions(PassOptions O) override;
  bool runOnModule(Module &M) override;

private:
  CallInst *m_OutputUAV = nullptr;
  int m_RemainingReservedSpaceInBytes = 0;
  Constant *m_OffsetMask = nullptr;
  SmallVector<Value *, 2> m_threadUniquifier;

  uint64_t m_UAVSize = 1024 * 1024;
  bool m_ExpandPayload = false;
  uint32_t m_DispatchArgumentY = 1;
  uint32_t m_DispatchArgumentZ = 1;
  uint32_t m_ExpandedPayloadSize = 0;
  uint32_t m_ExpandedPayloadAppendedFieldsOffset = 0;

  struct BuilderContext {
    Module &M;
    DxilModule &DM;
    LLVMContext &Ctx;
    OP *HlslOP;
    IRBuilder<> &Builder;
  };

  SmallVector<Value *, 2> insertInstructionsToCreateDisambiguationValue(
      IRBuilder<> &Builder, OP *HlslOP, LLVMContext &Ctx,
      unsigned appendedFieldsElementIndex, Instruction *firstGetPayload);
  Value *reserveDebugEntrySpace(BuilderContext &BC, uint32_t SpaceInBytes);
  uint32_t UAVDumpingGroundOffset();
  Value *writeDwordAndReturnNewOffset(BuilderContext &BC, Value *TheOffset,
                                      Value *TheValue);
  template <typename... T> void Instrument(BuilderContext &BC, T... values);
};

void DxilPIXMeshShaderOutputInstrumentation::applyOptions(PassOptions O) {
  GetPassOptionUInt64(O, "UAVSize", &m_UAVSize, 1024 * 1024);
  GetPassOptionBool(O, "expand-payload", &m_ExpandPayload, 0);
  GetPassOptionUInt32(O, "dispatchArgY", &m_DispatchArgumentY, 1);
  GetPassOptionUInt32(O, "dispatchArgZ", &m_DispatchArgumentZ, 1);
  GetPassOptionUInt32(O, "expanded-payload-size", &m_ExpandedPayloadSize, 0);
  GetPassOptionUInt32(O, "expanded-payload-offset",
                      &m_ExpandedPayloadAppendedFieldsOffset, 0);
}

uint32_t DxilPIXMeshShaderOutputInstrumentation::UAVDumpingGroundOffset() {
  return static_cast<uint32_t>(m_UAVSize - DebugBufferDumpingGroundSize);
}

Value *DxilPIXMeshShaderOutputInstrumentation::reserveDebugEntrySpace(
    BuilderContext &BC, uint32_t SpaceInBytes) {
  // Check the previous caller didn't reserve too much space:
  assert(m_RemainingReservedSpaceInBytes == 0);

  // Check that the caller isn't asking for so much memory that the writes will
  // run past the useful data and into the offset counter. Asking this of
  // m_RemainingReservedSpaceInBytes - which the assertion above has just
  // established is zero - tests a constant rather than the request, so it could
  // never fire whatever the caller passed.
  assert(SpaceInBytes < CounterOffsetBeyondUsefulData);

  m_RemainingReservedSpaceInBytes = SpaceInBytes;

  // Insert the UAV increment instruction:
  Function *AtomicOpFunc =
      BC.HlslOP->GetOpFunc(OP::OpCode::AtomicBinOp, Type::getInt32Ty(BC.Ctx));
  Constant *AtomicBinOpcode =
      BC.HlslOP->GetU32Const((unsigned)OP::OpCode::AtomicBinOp);
  Constant *AtomicAdd =
      BC.HlslOP->GetU32Const((unsigned)DXIL::AtomicBinOpCode::Add);
  Constant *OffsetArg = BC.HlslOP->GetU32Const(UAVDumpingGroundOffset() +
                                               CounterOffsetBeyondUsefulData);
  UndefValue *UndefArg = UndefValue::get(Type::getInt32Ty(BC.Ctx));

  Constant *Increment = BC.HlslOP->GetU32Const(SpaceInBytes);

  auto *PreviousValue = BC.Builder.CreateCall(
      AtomicOpFunc,
      {
          AtomicBinOpcode, // i32, ; opcode
          m_OutputUAV,     // %dx.types.Handle, ; resource handle
          AtomicAdd, // i32, ; binary operation code : EXCHANGE, IADD, AND, OR,
                     // XOR, IMIN, IMAX, UMIN, UMAX
          OffsetArg, // i32, ; coordinate c0: index in bytes
          UndefArg,  // i32, ; coordinate c1 (unused)
          UndefArg,  // i32, ; coordinate c2 (unused)
          Increment, // i32); increment value
      },
      "UAVIncResult");

  return BC.Builder.CreateAnd(PreviousValue, m_OffsetMask, "MaskedForUAVLimit");
}

Value *DxilPIXMeshShaderOutputInstrumentation::writeDwordAndReturnNewOffset(
    BuilderContext &BC, Value *TheOffset, Value *TheValue) {

  Function *StoreValue =
      BC.HlslOP->GetOpFunc(OP::OpCode::BufferStore, Type::getInt32Ty(BC.Ctx));
  Constant *StoreValueOpcode =
      BC.HlslOP->GetU32Const((unsigned)DXIL::OpCode::BufferStore);
  UndefValue *Undef32Arg = UndefValue::get(Type::getInt32Ty(BC.Ctx));
  Constant *WriteMask_X = BC.HlslOP->GetI8Const(1);

  (void)BC.Builder.CreateCall(
      StoreValue,
      {StoreValueOpcode, // i32 opcode
       m_OutputUAV,      // %dx.types.Handle, ; resource handle
       TheOffset,        // i32 c0: index in bytes into UAV
       Undef32Arg,       // i32 c1: unused
       TheValue,
       Undef32Arg, // unused values
       Undef32Arg, // unused values
       Undef32Arg, // unused values
       WriteMask_X});

  m_RemainingReservedSpaceInBytes -= sizeof(uint32_t);
  assert(m_RemainingReservedSpaceInBytes >=
         0); // or else the caller didn't reserve enough space

  return BC.Builder.CreateAdd(
      TheOffset,
      BC.HlslOP->GetU32Const(static_cast<unsigned int>(sizeof(uint32_t))));
}

template <typename... T>
void DxilPIXMeshShaderOutputInstrumentation::Instrument(BuilderContext &BC,
                                                        T... values) {
  llvm::SmallVector<llvm::Value *, 10> Values(
      {static_cast<llvm::Value *>(values)...});
  const uint32_t DwordCount = Values.size();
  llvm::Value *byteOffset =
      reserveDebugEntrySpace(BC, DwordCount * sizeof(uint32_t));
  for (llvm::Value *V : Values) {
    byteOffset = writeDwordAndReturnNewOffset(BC, byteOffset, V);
  }
}

Value *GetValueFromExpandedPayload(IRBuilder<> &Builder,
                                   Instruction *firstGetPayload,
                                   unsigned int offset, const char *name) {
  auto *DerefPointer = Builder.getInt32(0);
  auto *OffsetToExpandedData = Builder.getInt32(offset);
  auto *GEP = Builder.CreateGEP(
      cast<PointerType>(firstGetPayload->getType()->getScalarType())
          ->getElementType(),
      firstGetPayload, {DerefPointer, OffsetToExpandedData});
  return Builder.CreateLoad(GEP, name);
}

SmallVector<Value *, 2> DxilPIXMeshShaderOutputInstrumentation::
    insertInstructionsToCreateDisambiguationValue(
        IRBuilder<> &Builder, OP *HlslOP, LLVMContext &Ctx,
        unsigned appendedFieldsElementIndex, Instruction *firstGetPayload) {

  // When a mesh shader is called from an amplification shader, all of the
  // thread id values are relative to the DispatchMesh call made by
  // that amplification shader. Data about what thread counts were passed
  // by the CPU to *CommandList::DispatchMesh are not available, but we
  // will have added that value to the AS->MS payload...

  SmallVector<Value *, 2> ret;
  Constant *Zero32Arg = HlslOP->GetU32Const(0);

  bool AmplificationShaderIsActive = firstGetPayload != nullptr;

  llvm::Value *ASDispatchMeshYCount = nullptr;
  llvm::Value *ASDispatchMeshZCount = nullptr;
  if (AmplificationShaderIsActive) {

    auto *ASThreadId = GetValueFromExpandedPayload(
        Builder, firstGetPayload, appendedFieldsElementIndex, "ASThreadId");
    ret.push_back(ASThreadId);
    ASDispatchMeshYCount = GetValueFromExpandedPayload(
        Builder, firstGetPayload, appendedFieldsElementIndex + 1,
        "ASDispatchMeshYCount");
    ASDispatchMeshZCount = GetValueFromExpandedPayload(
        Builder, firstGetPayload, appendedFieldsElementIndex + 2,
        "ASDispatchMeshZCount");
  } else {
    ret.push_back(Zero32Arg);
  }

  Constant *One32Arg = HlslOP->GetU32Const(1);
  Constant *Two32Arg = HlslOP->GetU32Const(2);

  auto GroupIdFunc =
      HlslOP->GetOpFunc(DXIL::OpCode::GroupId, Type::getInt32Ty(Ctx));
  Constant *Opcode = HlslOP->GetU32Const((unsigned)DXIL::OpCode::GroupId);
  auto *GroupIdX =
      Builder.CreateCall(GroupIdFunc, {Opcode, Zero32Arg}, "GroupIdX");
  auto *GroupIdY =
      Builder.CreateCall(GroupIdFunc, {Opcode, One32Arg}, "GroupIdY");
  auto *GroupIdZ =
      Builder.CreateCall(GroupIdFunc, {Opcode, Two32Arg}, "GroupIdZ");

  // flattend group number = z + y*numZ + x*numY*numZ
  if (AmplificationShaderIsActive) {
    auto *GroupYxNumZ = Builder.CreateMul(GroupIdY, ASDispatchMeshZCount);
    auto *FlatGroupNumZY = Builder.CreateAdd(GroupIdZ, GroupYxNumZ);
    auto *GroupXxNumZ = Builder.CreateMul(GroupIdX, ASDispatchMeshZCount);
    auto *GroupXxNumYZ = Builder.CreateMul(GroupXxNumZ, ASDispatchMeshYCount);
    auto *FlatGroupNum = Builder.CreateAdd(GroupXxNumYZ, FlatGroupNumZY);
    ret.push_back(FlatGroupNum);
  } else {
    auto *GroupYxNumZ =
        Builder.CreateMul(GroupIdY, HlslOP->GetU32Const(m_DispatchArgumentZ));
    auto *FlatGroupNumZY = Builder.CreateAdd(GroupIdZ, GroupYxNumZ);
    auto *GroupXxNumYZ =
        Builder.CreateMul(GroupIdX, HlslOP->GetU32Const(m_DispatchArgumentY *
                                                        m_DispatchArgumentZ));
    auto *FlatGroupNum = Builder.CreateAdd(GroupXxNumYZ, FlatGroupNumZY);
    ret.push_back(FlatGroupNum);
  }

  return ret;
}

// The amplification shader pass appends its three disambiguation dwords after
// the last *field* of the amplification shader's payload struct, then re-rounds
// the total to that struct's alignment, and reports both the offset it placed
// them at and the resulting total size. D3D12 requires only that the two stages
// declare the same payload *size*; it says nothing about the field layout. Two
// same-sized payloads whose last fields end at different offsets therefore
// expand differently, so deriving the mesh shader's expanded layout from its
// own payload struct produces a shader that declares a size D3D rejects against
// the amplification shader's - PSO creation fails outright - and that reads the
// disambiguation values out of the wrong bytes.
//
// Rebuild the expanded type against the amplification shader's numbers instead.
// The mesh shader's own fields keep their element indices and their byte
// offsets, because its own payload reads have to stay correct; explicit i32
// padding then pushes the three appended dwords out to the reported offset and
// the total out to the reported size.
//
// Returns an empty ExpandedStruct when the two layouts cannot be reconciled,
// leaving the caller to fall back to the mesh shader's own expansion.
static ExpandedStruct BuildExpandedPayloadTypeMatchingAmplificationShader(
    Module &M, LLVMContext &Ctx, Type *OriginalPayloadStructType,
    uint32_t ExpandedSizeInBytes, uint32_t AppendedFieldsOffsetInBytes,
    unsigned *AppendedFieldsElementIndex) {
  ExpandedStruct ret = {};

  auto *OriginalStructType = dyn_cast<StructType>(OriginalPayloadStructType);
  if (OriginalStructType == nullptr || OriginalStructType->isOpaque()) {
    return ret;
  }

  constexpr uint32_t AppendedFieldsSizeInBytes = 3 * sizeof(uint32_t);
  // The offset is bounded before it is added to anything, so the sum below
  // cannot wrap.
  if (AppendedFieldsOffsetInBytes % sizeof(uint32_t) != 0 ||
      AppendedFieldsOffsetInBytes > DXIL::kMaxMSASPayloadBytes ||
      ExpandedSizeInBytes % sizeof(uint32_t) != 0 ||
      ExpandedSizeInBytes <
          AppendedFieldsOffsetInBytes + AppendedFieldsSizeInBytes ||
      ExpandedSizeInBytes > DXIL::kMaxMSASPayloadBytes) {
    return ret;
  }

  const DataLayout &DL = M.getDataLayout();
  const StructLayout *OriginalLayout = DL.getStructLayout(OriginalStructType);
  auto *Int32Type = Type::getInt32Ty(Ctx);
  const unsigned OriginalElementCount = OriginalStructType->getNumElements();

  // A struct's alloc size is rounded up to its own alignment, so a mesh shader
  // payload containing a 64-bit member can only ever reach a total that is a
  // multiple of eight. The amplification shader's total is under no such
  // constraint. A packed struct - whose alignment is one - is the only way to
  // express the difference, so it is tried as a fallback, and only accepted if
  // it happens to leave the mesh shader's own fields exactly where they were:
  // dropping the padding between them would silently corrupt every payload
  // read the shader makes.
  const bool PackedCandidates[] = {false, true};
  for (bool Packed : PackedCandidates) {
    SmallVector<Type *, 16> Elements;
    for (unsigned i = 0; i < OriginalElementCount; ++i) {
      Elements.push_back(OriginalStructType->getElementType(i));
    }

    // Where the first appended dword would land with no padding at all.
    Elements.push_back(Int32Type);
    Elements.push_back(Int32Type);
    Elements.push_back(Int32Type);
    uint64_t UnpaddedOffsetInBytes =
        DL.getStructLayout(StructType::get(Ctx, Elements, Packed))
            ->getElementOffset(OriginalElementCount);
    Elements.resize(OriginalElementCount);

    if (UnpaddedOffsetInBytes > AppendedFieldsOffsetInBytes) {
      // The mesh shader's own fields run past the point at which the
      // amplification shader wrote the appended values, so no one struct can
      // describe both.
      continue;
    }

    unsigned AppendedIndex = OriginalElementCount;
    uint64_t MidPaddingInBytes =
        AppendedFieldsOffsetInBytes - UnpaddedOffsetInBytes;
    if (MidPaddingInBytes != 0) {
      // Padding is expressed in i32 rather than i8 because DXIL's data layout
      // aligns i8 to 32 bits, which would make a byte array four times the
      // size intended. A padding run that is not a whole number of dwords
      // cannot be expressed this way, and the layout assertions below reject
      // the truncated result rather than emitting a wrong offset.
      Elements.push_back(
          ArrayType::get(Int32Type, MidPaddingInBytes / sizeof(uint32_t)));
      ++AppendedIndex;
    }
    Elements.push_back(Int32Type);
    Elements.push_back(Int32Type);
    Elements.push_back(Int32Type);
    uint32_t TailPaddingInBytes = ExpandedSizeInBytes -
                                  AppendedFieldsOffsetInBytes -
                                  AppendedFieldsSizeInBytes;
    if (TailPaddingInBytes != 0) {
      Elements.push_back(
          ArrayType::get(Int32Type, TailPaddingInBytes / sizeof(uint32_t)));
    }

    // Everything above reasons about where the data layout ought to put these
    // elements; ask it instead. A layout that misses the reported offset or the
    // reported size by even one byte is worse than no instrumentation at all,
    // and the mistake would only surface as a failed PSO creation on someone
    // else's machine.
    StructType *Candidate = StructType::get(Ctx, Elements, Packed);
    const StructLayout *CandidateLayout = DL.getStructLayout(Candidate);
    if (DL.getTypeAllocSize(Candidate) != ExpandedSizeInBytes ||
        CandidateLayout->getElementOffset(AppendedIndex) !=
            AppendedFieldsOffsetInBytes) {
      continue;
    }
    bool OriginalFieldsUnmoved = true;
    for (unsigned i = 0; i < OriginalElementCount; ++i) {
      if (CandidateLayout->getElementOffset(i) !=
          OriginalLayout->getElementOffset(i)) {
        OriginalFieldsUnmoved = false;
        break;
      }
    }
    if (!OriginalFieldsUnmoved) {
      continue;
    }

    *AppendedFieldsElementIndex = AppendedIndex;
    ret.ExpandedPayloadStructType =
        StructType::create(Ctx, Elements, "PIX_AS2MS_Expanded_Type", Packed);
    ret.ExpandedPayloadStructPtrType =
        ret.ExpandedPayloadStructType->getPointerTo();
    return ret;
  }

  return ret;
}

// A mesh shader that never reads its payload has no GetMeshPayload call, so the
// payload struct type is absent from this module altogether and the expanded
// layout cannot be recovered from it. The declared payload size is no
// substitute: the amplification shader appends its three values after the
// original payload's last *field* and then re-rounds the total to the
// original's alignment, so two payloads with the same declared size can expand
// to different offsets and different totals. The amplification shader pass
// therefore reports the layout it produced and PIX forwards it here.
//
// Rebuild an equivalent type: the original payload becomes an opaque blob of
// i32 (this pass has no interest in its contents), the three appended values
// follow at the reported offset, and explicit tail padding makes the total
// match the amplification shader's declared size exactly. Every element is
// 4-byte aligned or smaller, so the synthesized struct's alloc size equals its
// store size and no implicit padding can creep in. Getting this wrong is fatal
// rather than merely inaccurate: D3D rejects PSO creation outright when the two
// stages disagree about the payload size.
static ExpandedStruct
SynthesizeExpandedPayloadType(LLVMContext &Ctx, uint32_t ExpandedSizeInBytes,
                              uint32_t AppendedFieldsOffsetInBytes) {
  ExpandedStruct ret = {};

  constexpr uint32_t AppendedFieldsSizeInBytes = 3 * sizeof(uint32_t);
  // The offset is bounded before it is added to anything: an offset near
  // UINT32_MAX would make the sum below wrap to a small number, pass every
  // remaining check, and produce a multi-gigabyte padding array.
  if (AppendedFieldsOffsetInBytes % sizeof(uint32_t) != 0 ||
      AppendedFieldsOffsetInBytes > DXIL::kMaxMSASPayloadBytes ||
      ExpandedSizeInBytes % sizeof(uint32_t) != 0 ||
      ExpandedSizeInBytes <
          AppendedFieldsOffsetInBytes + AppendedFieldsSizeInBytes ||
      ExpandedSizeInBytes > DXIL::kMaxMSASPayloadBytes) {
    return ret;
  }

  auto *Int32Type = Type::getInt32Ty(Ctx);
  auto *OpaqueOriginalPayloadType = ArrayType::get(
      Int32Type, AppendedFieldsOffsetInBytes / sizeof(uint32_t));

  // The opaque blob is a single element, so the three appended values land at
  // element indices 1, 2 and 3 - which is what the caller passes as the
  // appended-fields element index.
  SmallVector<Type *, 5> Elements{OpaqueOriginalPayloadType, Int32Type,
                                  Int32Type, Int32Type};
  uint32_t TailPaddingInBytes = ExpandedSizeInBytes -
                                AppendedFieldsOffsetInBytes -
                                AppendedFieldsSizeInBytes;
  if (TailPaddingInBytes != 0) {
    // Padding is expressed in i32 rather than i8 because DXIL's data layout
    // aligns i8 to 32 bits, which would make a byte array four times the size
    // intended. Both the appended fields' offset and the expanded total are
    // 4-byte aligned, so the padding between them always divides evenly.
    Elements.push_back(
        ArrayType::get(Int32Type, TailPaddingInBytes / sizeof(uint32_t)));
  }

  ret.ExpandedPayloadStructType =
      StructType::create(Ctx, Elements, "PIX_AS2MS_Expanded_Type");
  ret.ExpandedPayloadStructPtrType =
      ret.ExpandedPayloadStructType->getPointerTo();
  return ret;
}

// The mesh shader's output signature is the only place the distinction between
// int16_t and uint16_t survives, because DXIL's i16 is signless and both share
// the storeVertexOutput.i16 overload. Returns false whenever the element cannot
// be identified, which preserves the historical zero-extension.
static bool OutputSignatureElementIsSigned(DxilModule &DM, Value *OutputSigId) {
  auto *SigIdConstant = dyn_cast<ConstantInt>(OutputSigId);
  if (SigIdConstant == nullptr) {
    // A dynamically indexed output has no single signature element to consult.
    return false;
  }
  const DxilSignature &OutputSignature = DM.GetOutputSignature();
  uint64_t SigId = SigIdConstant->getLimitedValue();
  if (SigId >= OutputSignature.GetElements().size()) {
    return false;
  }
  return OutputSignature.GetElement(static_cast<unsigned>(SigId))
      .GetCompType()
      .IsSIntTy();
}

bool DxilPIXMeshShaderOutputInstrumentation::runOnModule(Module &M) {
  DxilModule &DM = M.GetOrCreateDxilModule();
  LLVMContext &Ctx = M.getContext();
  OP *HlslOP = DM.GetOP();

  Type *OriginalPayloadStructType = nullptr;
  ExpandedStruct expanded = {};
  unsigned AppendedFieldsElementIndex = 0;
  Instruction *FirstNewStructGetMeshPayload = nullptr;
  if (m_ExpandPayload) {
    Instruction *getMeshPayloadInstructions = nullptr;
    llvm::Function *entryFunction = PIXPassHelpers::GetEntryFunction(DM);
    for (inst_iterator I = inst_begin(entryFunction),
                       E = inst_end(entryFunction);
         I != E; ++I) {
      if (auto *Instr = llvm::cast<Instruction>(&*I)) {
        if (hlsl::OP::IsDxilOpFuncCallInst(Instr,
                                           hlsl::OP::OpCode::GetMeshPayload)) {
          getMeshPayloadInstructions = Instr;
          Type *OriginalPayloadStructPointerType = Instr->getType();
          OriginalPayloadStructType =
              OriginalPayloadStructPointerType->getPointerElementType();
          // The validator assures that there is only one call to
          // GetMeshPayload...
          break;
        }
      }
    }

    if (OriginalPayloadStructType != nullptr) {
      if (m_ExpandedPayloadSize != 0) {
        // PIX forwards the layout the amplification shader pass actually
        // produced, and that layout is authoritative: D3D refuses to create the
        // PSO unless both stages declare the same payload size, and the
        // amplification shader has already written the disambiguation values at
        // the offset it reported.
        expanded = BuildExpandedPayloadTypeMatchingAmplificationShader(
            M, Ctx, OriginalPayloadStructType, m_ExpandedPayloadSize,
            m_ExpandedPayloadAppendedFieldsOffset,
            &AppendedFieldsElementIndex);
      }
      if (expanded.ExpandedPayloadStructPtrType == nullptr) {
        // Either PIX did not tell us what the amplification shader did (no
        // amplification shader, or an older PIX), or the two layouts cannot be
        // reconciled. Expanding the mesh shader's own struct is what this pass
        // has always done and is right whenever both stages declare the same
        // struct.
        expanded = ExpandStructType(Ctx, OriginalPayloadStructType);
        AppendedFieldsElementIndex =
            OriginalPayloadStructType->getStructNumElements();
        unsigned expandedPayloadSizeInBytes =
            (unsigned)M.getDataLayout().getTypeAllocSize(
                expanded.ExpandedPayloadStructType);
        if (expandedPayloadSizeInBytes > DXIL::kMaxMSASPayloadBytes) {
          expanded = {};
        }
      }

      if (expanded.ExpandedPayloadStructPtrType != nullptr &&
          getMeshPayloadInstructions != nullptr) {

        llvm::Function *OriginalGetMeshPayloadFunction =
            cast<CallInst>(getMeshPayloadInstructions)->getCalledFunction();

        Function *DxilFunc = HlslOP->GetOpFunc(
            OP::OpCode::GetMeshPayload, expanded.ExpandedPayloadStructPtrType);
        Constant *opArg =
            HlslOP->GetU32Const((unsigned)OP::OpCode::GetMeshPayload);
        IRBuilder<> Builder(getMeshPayloadInstructions);
        Value *args[] = {opArg};
        Instruction *payload = Builder.CreateCall(DxilFunc, args);

        if (FirstNewStructGetMeshPayload == nullptr) {
          FirstNewStructGetMeshPayload = payload;
        }

        ReplaceAllUsesOfInstructionWithNewValueAndDeleteInstruction(
            getMeshPayloadInstructions, payload,
            expanded.ExpandedPayloadStructType);

        // The replacement call uses the expanded payload overload, so deleting
        // the original call leaves the original overload declared and uncalled.
        PIXPassHelpers::EraseIfUnused(DM, OriginalGetMeshPayloadFunction);
      }
    } else if (m_ExpandedPayloadSize != 0) {
      // The mesh shader never reads the payload, but the amplification shader
      // expanded it regardless, so this shader still has to declare the larger
      // size or PSO creation fails. Synthesize a matching payload access so the
      // per-invocation disambiguation values remain readable; without them,
      // mesh output records from different amplification shader threads would
      // collide and overwrite each other.
      expanded = SynthesizeExpandedPayloadType(
          Ctx, m_ExpandedPayloadSize, m_ExpandedPayloadAppendedFieldsOffset);
      if (expanded.ExpandedPayloadStructPtrType != nullptr) {
        // The synthesized type puts the whole original payload in one opaque
        // element, so the three appended values follow it at indices 1..3.
        AppendedFieldsElementIndex = 1;
        IRBuilder<> Builder(dxilutil::FirstNonAllocaInsertionPt(
            PIXPassHelpers::GetEntryFunction(DM)));
        Function *DxilFunc = HlslOP->GetOpFunc(
            OP::OpCode::GetMeshPayload, expanded.ExpandedPayloadStructPtrType);
        Constant *opArg =
            HlslOP->GetU32Const((unsigned)OP::OpCode::GetMeshPayload);
        Value *args[] = {opArg};
        FirstNewStructGetMeshPayload = Builder.CreateCall(DxilFunc, args);
      }
    }
  }

  Instruction *firstInsertionPt =
      dxilutil::FirstNonAllocaInsertionPt(GetEntryFunction(DM));
  IRBuilder<> Builder(firstInsertionPt);

  BuilderContext BC{M, DM, Ctx, HlslOP, Builder};

  m_OffsetMask = BC.HlslOP->GetU32Const(UAVDumpingGroundOffset() - 1);

  m_OutputUAV = CreateUAVOnceForModule(DM, Builder, 0, "PIX_DebugUAV_Handle");

  if (FirstNewStructGetMeshPayload == nullptr) {
    Instruction *firstInsertionPt = dxilutil::FirstNonAllocaInsertionPt(
        PIXPassHelpers::GetEntryFunction(DM));
    IRBuilder<> Builder(firstInsertionPt);
    m_threadUniquifier = insertInstructionsToCreateDisambiguationValue(
        Builder, HlslOP, Ctx, 0, nullptr);
  } else {
    IRBuilder<> Builder(FirstNewStructGetMeshPayload->getNextNode());
    m_threadUniquifier = insertInstructionsToCreateDisambiguationValue(
        Builder, HlslOP, Ctx, AppendedFieldsElementIndex,
        FirstNewStructGetMeshPayload);
  }

  auto F = HlslOP->GetOpFunc(DXIL::OpCode::EmitIndices, Type::getVoidTy(Ctx));
  auto FunctionUses = F->uses();
  for (auto FI = FunctionUses.begin(); FI != FunctionUses.end();) {
    auto &FunctionUse = *FI++;
    auto FunctionUser = FunctionUse.getUser();

    auto Call = cast<CallInst>(FunctionUser);

    IRBuilder<> Builder2(Call);
    BuilderContext BC2{M, DM, Ctx, HlslOP, Builder2};

    Instrument(BC2, BC2.HlslOP->GetI32Const(triangleIndexIndicator),
               m_threadUniquifier[0], m_threadUniquifier[1],
               Call->getOperand(1), Call->getOperand(2), Call->getOperand(3),
               Call->getOperand(4));
  }

  // EmitIndices is looked up unconditionally above, and OP::GetOpFunc
  // materialises the declaration on demand, so a mesh shader that emits no
  // indices at all - it has no "out indices" parameter, or has one it never
  // assigns - is left with an external declaration that nothing calls. dxv
  // rejects that ("External function 'dx.op.emitIndices' is unused"). Erase it
  // here rather than after the loop below, which reassigns F.
  PIXPassHelpers::EraseIfUnused(DM, F);

  struct OutputType {
    Type *type;
    uint32_t tag;
  };

  SmallVector<OutputType, 4> StoreVertexOutputOverloads{
      {Type::getInt32Ty(Ctx), int32ValueIndicator},
      {Type::getInt16Ty(Ctx), int16ValueIndicator},
      {Type::getFloatTy(Ctx), floatValueIndicator},
      {Type::getHalfTy(Ctx), float16ValueIndicator}};

  SmallVector<Function *, 4> StoreVertexOutputFunctions;

  for (auto const &Overload : StoreVertexOutputOverloads) {
    F = HlslOP->GetOpFunc(DXIL::OpCode::StoreVertexOutput, Overload.type);
    StoreVertexOutputFunctions.push_back(F);
    FunctionUses = F->uses();
    for (auto FI = FunctionUses.begin(); FI != FunctionUses.end();) {
      auto &FunctionUse = *FI++;
      auto FunctionUser = FunctionUse.getUser();

      auto Call = cast<CallInst>(FunctionUser);

      IRBuilder<> Builder2(Call);
      BuilderContext BC2{M, DM, Ctx, HlslOP, Builder2};

      // Expand column index to 32 bits:
      auto ColumnIndex = BC2.Builder.CreateCast(
          Instruction::ZExt, Call->getOperand(3), Type::getInt32Ty(Ctx));

      // Coerce actual value to int32
      Value *CoercedValue = Call->getOperand(4);

      if (Overload.tag == floatValueIndicator) {
        CoercedValue = BC2.Builder.CreateCast(
            Instruction::BitCast, CoercedValue, Type::getInt32Ty(Ctx));
      } else if (Overload.tag == float16ValueIndicator) {
        auto *HalfInt = BC2.Builder.CreateCast(
            Instruction::BitCast, CoercedValue, Type::getInt16Ty(Ctx));

        CoercedValue = BC2.Builder.CreateCast(Instruction::ZExt, HalfInt,
                                              Type::getInt32Ty(Ctx));
      } else if (Overload.tag == int16ValueIndicator) {
        // DXIL's i16 is signless, so this one overload carries both int16_t and
        // uint16_t outputs. PIX re-widens the recorded dword by the signature
        // element's component type but never restores the sign, so a
        // zero-extended int16_t of -1 reaches the mesh output viewer as 65535.
        // The output signature is the only place the signedness survives into
        // this pass.
        Instruction::CastOps ExtensionKind =
            OutputSignatureElementIsSigned(DM, Call->getOperand(1))
                ? Instruction::SExt
                : Instruction::ZExt;
        CoercedValue = BC2.Builder.CreateCast(ExtensionKind, CoercedValue,
                                              Type::getInt32Ty(Ctx));
      }

      Instrument(BC2, BC2.HlslOP->GetI32Const(Overload.tag),
                 m_threadUniquifier[0], m_threadUniquifier[1],
                 Call->getOperand(1), Call->getOperand(2), ColumnIndex,
                 CoercedValue, Call->getOperand(5));
    }
  }

  // A mesh shader only ever writes some of the four vertex-output types, but
  // instrumenting them all means looking all four overloads up. Whichever went
  // unused would otherwise be left as a dead external declaration, which fails
  // validation.
  for (Function *StoreVertexOutputFunction : StoreVertexOutputFunctions) {
    PIXPassHelpers::EraseIfUnused(DM, StoreVertexOutputFunction);
  }

  // If the AS->MS payload struct was expanded, the entry point's declared
  // payload size must grow to match the expanded struct. Use the expanded
  // struct's alloc size (including tail padding) so it equals the size the
  // amplification shader now writes, keeping the DXIL validator happy.
  if (expanded.ExpandedPayloadStructType != nullptr) {
    DM.GetDxilFunctionProps(PIXPassHelpers::GetEntryFunction(DM))
        .ShaderProps.MS.payloadSizeInBytes =
        (unsigned)M.getDataLayout().getTypeAllocSize(
            expanded.ExpandedPayloadStructType);
  }

  DM.ReEmitDxilResources();

  return true;
}

char DxilPIXMeshShaderOutputInstrumentation::ID = 0;

ModulePass *llvm::createDxilDxilPIXMeshShaderOutputInstrumentation() {
  return new DxilPIXMeshShaderOutputInstrumentation();
}

INITIALIZE_PASS(DxilPIXMeshShaderOutputInstrumentation,
                "hlsl-dxil-pix-meshshader-output-instrumentation",
                "DXIL mesh shader output instrumentation for PIX", false, false)
