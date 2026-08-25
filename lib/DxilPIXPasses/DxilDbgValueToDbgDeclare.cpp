///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// DxilDbgValueToDbgDeclare.cpp                                              //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// Converts calls to llvm.dbg.value to llvm.dbg.declare + alloca + stores.   //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include <algorithm>
#include <map>
#include <memory>
#include <unordered_map>
#include <utility>

#include "dxc/DXIL/DxilConstants.h"
#include "dxc/DXIL/DxilModule.h"
#include "dxc/DXIL/DxilOperations.h"
#include "dxc/DXIL/DxilResourceBase.h"
#include "dxc/DxilPIXPasses/DxilPIXPasses.h"
#include "llvm/ADT/STLExtras.h"
#include "llvm/IR/DIBuilder.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/Intrinsics.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"

#include "PixPassHelpers.h"
using namespace PIXPassHelpers;

using namespace llvm;

// #define VALUE_TO_DECLARE_LOGGING

#ifdef VALUE_TO_DECLARE_LOGGING
#ifndef PIX_DEBUG_DUMP_HELPER
#error Turn on PIX_DEBUG_DUMP_HELPER in PixPassHelpers.h
#endif
#define VALUE_TO_DECLARE_LOG Log
#else
#define VALUE_TO_DECLARE_LOG(...)
#endif

#define DEBUG_TYPE "dxil-dbg-value-to-dbg-declare"

namespace {
using OffsetInBits = unsigned;
using SizeInBits = unsigned;
struct Offsets {
  OffsetInBits Aligned;
  OffsetInBits Packed;
};

// DITypePeelTypeAlias peels const, typedef, and other alias types off of Ty,
// returning the unalised type.
static llvm::DIType *DITypePeelTypeAlias(llvm::DIType *Ty) {
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    const llvm::DITypeIdentifierMap EmptyMap;
    switch (DerivedTy->getTag()) {
    case llvm::dwarf::DW_TAG_restrict_type:
    case llvm::dwarf::DW_TAG_reference_type:
    case llvm::dwarf::DW_TAG_const_type:
    case llvm::dwarf::DW_TAG_typedef:
    case llvm::dwarf::DW_TAG_pointer_type:
      return DITypePeelTypeAlias(DerivedTy->getBaseType().resolve(EmptyMap));
    case llvm::dwarf::DW_TAG_member:
      return DITypePeelTypeAlias(DerivedTy->getBaseType().resolve(EmptyMap));
    }
  }

  return Ty;
}

llvm::DIBasicType *BaseTypeIfItIsBasicAndLarger(llvm::DIType *Ty) {
  // Working around problems with bitfield size/alignment:
  // For bitfield types, size may be < 32, but the underlying type
  // will have the size of that basic type, e.g. 32 for ints.
  // By contrast, for min16float, size will be 16, but align will be 16 or 32
  // depending on whether or not 16-bit is enabled.
  // So if we find a disparity in size, we can assume it's not e.g. min16float.
  auto *baseType = DITypePeelTypeAlias(Ty);
  if (Ty->getSizeInBits() != 0 &&
      Ty->getSizeInBits() < baseType->getSizeInBits())
    return llvm::dyn_cast<llvm::DIBasicType>(baseType);
  return nullptr;
}

// OffsetManager is used to map between "packed" and aligned offsets.
//
// For example, the aligned offsets for a struct [float, half, int, double]
// will be {0, 32, 64, 128} (assuming 32 bit alignments for ints, and 64
// bit for doubles), while the packed offsets will be {0, 32, 48, 80}.
//
// This mapping makes it easier to deal with llvm.dbg.values whose value
// operand does not match exactly the Variable operand's type.
class OffsetManager {
  unsigned DescendTypeToGetAlignMask(llvm::DIType *Ty) {
    unsigned AlignMask = Ty->getAlignInBits();
    if (BaseTypeIfItIsBasicAndLarger(Ty))
      AlignMask = 0;
    else {
      auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty);
      if (DerivedTy != nullptr) {
        // Working around a bug where byte size is stored instead of bit size
        if (AlignMask == 4 && Ty->getSizeInBits() == 32) {
          AlignMask = 32;
        }
        if (AlignMask == 0) {
          const llvm::DITypeIdentifierMap EmptyMap;
          switch (DerivedTy->getTag()) {
          case llvm::dwarf::DW_TAG_restrict_type:
          case llvm::dwarf::DW_TAG_reference_type:
          case llvm::dwarf::DW_TAG_const_type:
          case llvm::dwarf::DW_TAG_typedef: {
            llvm::DIType *baseType = DerivedTy->getBaseType().resolve(EmptyMap);
            if (baseType != nullptr) {
              return DescendTypeToGetAlignMask(baseType);
            }
          }
          }
        }
      }
    }
    return AlignMask;
  }

public:
  OffsetManager() = default;

  // AlignTo aligns the current aligned offset to Ty's natural alignment.
  void AlignTo(llvm::DIType *Ty) {
    unsigned AlignMask = DescendTypeToGetAlignMask(Ty);
    if (AlignMask) {
      VALUE_TO_DECLARE_LOG("Aligning to %d", AlignMask);
      m_CurrentAlignedOffset =
          llvm::RoundUpToAlignment(m_CurrentAlignedOffset, AlignMask);
    } else {
      VALUE_TO_DECLARE_LOG("Failed to find alignment");
    }
  }

  // Move the aligned offset forward without adding padding to the packed
  // offset. Overlapping debug information cannot move storage mappings
  // backward.
  void AdvanceAlignedOffsetTo(OffsetInBits AlignedOffset) {
    if (AlignedOffset > m_CurrentAlignedOffset) {
      VALUE_TO_DECLARE_LOG("Advancing aligned offset from %d to %d",
                           m_CurrentAlignedOffset, AlignedOffset);
      m_CurrentAlignedOffset = AlignedOffset;
    } else if (AlignedOffset < m_CurrentAlignedOffset) {
      VALUE_TO_DECLARE_LOG("Refusing to move aligned offset back from %d to %d",
                           m_CurrentAlignedOffset, AlignedOffset);
      // Keep existing mappings monotonic when debug information overlaps.
      return;
    }
  }

  // Add is used to "add" an aggregate element (struct field, array element)
  // at the current aligned/packed offsets, bumping them by Ty's size.
  Offsets Add(llvm::DIBasicType *Ty, unsigned sizeOverride) {
    VALUE_TO_DECLARE_LOG("Adding known type at aligned %d / packed %d, size %d",
                         m_CurrentAlignedOffset, m_CurrentPackedOffset,
                         Ty->getSizeInBits());

    m_PackedOffsetToAlignedOffset[m_CurrentPackedOffset] =
        m_CurrentAlignedOffset;
    m_AlignedOffsetToPackedOffset[m_CurrentAlignedOffset] =
        m_CurrentPackedOffset;

    const Offsets Ret = {m_CurrentAlignedOffset, m_CurrentPackedOffset};
    unsigned size = sizeOverride != 0 ? sizeOverride : Ty->getSizeInBits();
    m_CurrentPackedOffset += size;
    m_CurrentAlignedOffset += size;

    return Ret;
  }

  // AlignToAndAddUnhandledType is used for error handling when Ty
  // could not be handled by the transformation. This is a best-effort
  // way to continue the pass by ignoring the current type and hoping
  // that adding Ty as a blob other fields/elements added will land
  // in the proper offset.
  void AlignToAndAddUnhandledType(llvm::DIType *Ty) {
    VALUE_TO_DECLARE_LOG(
        "Adding unhandled type at aligned %d / packed %d, size %d",
        m_CurrentAlignedOffset, m_CurrentPackedOffset, Ty->getSizeInBits());
    AlignTo(Ty);
    m_CurrentPackedOffset += Ty->getSizeInBits();
    m_CurrentAlignedOffset += Ty->getSizeInBits();
  }

  void AddResourceType(llvm::DIType *Ty) {
    VALUE_TO_DECLARE_LOG(
        "Adding resource type at aligned %d / packed %d, size %d",
        m_CurrentAlignedOffset, m_CurrentPackedOffset, Ty->getSizeInBits());
    m_PackedOffsetToAlignedOffset[m_CurrentPackedOffset] =
        m_CurrentAlignedOffset;
    m_AlignedOffsetToPackedOffset[m_CurrentAlignedOffset] =
        m_CurrentPackedOffset;

    m_CurrentPackedOffset += Ty->getSizeInBits();
    m_CurrentAlignedOffset += Ty->getSizeInBits();
  }

  bool GetAlignedOffsetFromPackedOffset(OffsetInBits PackedOffset,
                                        OffsetInBits *AlignedOffset) const {
    return GetOffsetWithMap(m_PackedOffsetToAlignedOffset, PackedOffset,
                            AlignedOffset);
  }

  bool GetPackedOffsetFromAlignedOffset(OffsetInBits AlignedOffset,
                                        OffsetInBits *PackedOffset) const {
    return GetOffsetWithMap(m_AlignedOffsetToPackedOffset, AlignedOffset,
                            PackedOffset);
  }

  OffsetInBits GetCurrentPackedOffset() const { return m_CurrentPackedOffset; }

  OffsetInBits GetCurrentAlignedOffset() const {
    return m_CurrentAlignedOffset;
  }

private:
  OffsetInBits m_CurrentPackedOffset = 0;
  OffsetInBits m_CurrentAlignedOffset = 0;

  using OffsetMap = std::unordered_map<OffsetInBits, OffsetInBits>;

  OffsetMap m_PackedOffsetToAlignedOffset;
  OffsetMap m_AlignedOffsetToPackedOffset;

  static bool GetOffsetWithMap(const OffsetMap &Map, OffsetInBits SrcOffset,
                               OffsetInBits *DstOffset) {
    auto it = Map.find(SrcOffset);
    if (it == Map.end()) {
      return false;
    }

    *DstOffset = it->second;
    return true;
  }
};

// VariableRegisters contains the logic for traversing a DIType T and
// creating AllocaInsts that map back to a specific offset within T.
class VariableRegisters {
public:
  VariableRegisters(llvm::DebugLoc const &m_dbgLoc,
                    llvm::BasicBlock::iterator allocaInsertionPoint,
                    llvm::DIVariable *Variable, llvm::DIType *Ty,
                    llvm::Module *M);

  llvm::AllocaInst *
  GetRegisterForAlignedOffset(OffsetInBits AlignedOffset) const;

  const OffsetManager &GetOffsetManager() const { return m_Offsets; }

  static SizeInBits GetVariableSizeInbits(DIVariable *Var);

private:
  void PopulateAllocaMap(llvm::DIType *Ty);

  void PopulateAllocaMap_BasicType(llvm::DIBasicType *Ty,
                                   unsigned sizeOverride);

  void PopulateAllocaMap_ArrayType(llvm::DICompositeType *Ty);

  void PopulateAllocaMap_StructType(llvm::DICompositeType *Ty);

  llvm::DILocation *GetVariableLocation() const;
  llvm::Value *GetMetadataAsValue(llvm::Metadata *M) const;
  llvm::DIExpression *GetDIExpression(llvm::DIType *Ty, OffsetInBits Offset,
                                      SizeInBits ParentSize,
                                      unsigned sizeOverride) const;

  llvm::DebugLoc const &m_dbgLoc;
  llvm::DIVariable *m_Variable = nullptr;
  llvm::IRBuilder<> m_B;
  llvm::Function *m_DbgDeclareFn = nullptr;

  OffsetManager m_Offsets;
  std::unordered_map<OffsetInBits, llvm::AllocaInst *> m_AlignedOffsetToAlloca;
};

struct GlobalEmbeddedArrayElementStorage {
  std::string Name;
  OffsetInBits Offset;
  SizeInBits Size;
};
using GlobalVariableToLocalMirrorMap =
    std::map<llvm::Function const *, llvm::DILocalVariable *>;
struct LocalMirrorsAndStorage {
  std::vector<GlobalEmbeddedArrayElementStorage> ArrayElementStorage;
  GlobalVariableToLocalMirrorMap LocalMirrors;
};
using GlobalStorageMap =
    std::map<llvm::DIGlobalVariable *, LocalMirrorsAndStorage>;

class DxilDbgValueToDbgDeclare : public llvm::ModulePass {
public:
  static char ID;
  DxilDbgValueToDbgDeclare() : llvm::ModulePass(ID) {}
  bool runOnModule(llvm::Module &M) override;

private:
  void handleDbgValue(llvm::Module &M, llvm::DbgValueInst *DbgValue);
  bool handleStoreIfDestIsGlobal(llvm::Module &M,
                                 GlobalStorageMap &GlobalStorage,
                                 llvm::StoreInst *Store);

  std::unordered_map<llvm::DIVariable *, std::unique_ptr<VariableRegisters>>
      m_Registers;
};
} // namespace

char DxilDbgValueToDbgDeclare::ID = 0;

struct ValueAndOffset {
  llvm::Value *m_V;
  OffsetInBits m_PackedOffset;
};

// SplitValue splits an llvm::Value into possibly multiple
// scalar Values. Those scalar values will later be "stored"
// into their corresponding register.
static OffsetInBits SplitValue(llvm::Value *V, OffsetInBits CurrentOffset,
                               std::vector<ValueAndOffset> *Values,
                               llvm::IRBuilder<> &B) {
  auto *VTy = V->getType();
  if (auto *ArrTy = llvm::dyn_cast<llvm::ArrayType>(VTy)) {
    for (unsigned i = 0; i < ArrTy->getNumElements(); ++i) {
      CurrentOffset =
          SplitValue(B.CreateExtractValue(V, {i}), CurrentOffset, Values, B);
    }
  } else if (auto *StTy = llvm::dyn_cast<llvm::StructType>(VTy)) {
    for (unsigned i = 0; i < StTy->getNumElements(); ++i) {
      CurrentOffset =
          SplitValue(B.CreateExtractValue(V, {i}), CurrentOffset, Values, B);
    }
  } else if (auto *VecTy = llvm::dyn_cast<llvm::VectorType>(VTy)) {
    for (unsigned i = 0; i < VecTy->getNumElements(); ++i) {
      CurrentOffset =
          SplitValue(B.CreateExtractElement(V, i), CurrentOffset, Values, B);
    }
  } else {
    assert(VTy->isFloatTy() || VTy->isDoubleTy() || VTy->isHalfTy() ||
           VTy->isIntegerTy(32) || VTy->isIntegerTy(64) ||
           VTy->isIntegerTy(16) || VTy->isPointerTy());
    Values->emplace_back(ValueAndOffset{V, CurrentOffset});
    CurrentOffset += VTy->getScalarSizeInBits();
  }

  return CurrentOffset;
}

// A more convenient version of SplitValue.
static std::vector<ValueAndOffset>
SplitValue(llvm::Value *V, OffsetInBits CurrentOffset, llvm::IRBuilder<> &B) {
  std::vector<ValueAndOffset> Ret;
  SplitValue(V, CurrentOffset, &Ret, B);
  return Ret;
}

// Convenient helper for parsing a DIExpression's offset.
static OffsetInBits GetAlignedOffsetFromDIExpression(llvm::DIExpression *Exp) {
  if (!Exp->isBitPiece()) {
    return 0;
  }

  return Exp->getBitPieceOffset();
}

llvm::DISubprogram *GetFunctionDebugInfo(llvm::Module &M, llvm::Function *fn) {
  auto FnMap = makeSubprogramMap(M);
  return FnMap[fn];
}

GlobalVariableToLocalMirrorMap
GenerateGlobalToLocalMirrorMap(llvm::Module &M, llvm::DIGlobalVariable *DIGV) {
  auto &Functions = M.getFunctionList();

  std::string LocalMirrorOfGlobalName =
      std::string("global.") + std::string(DIGV->getName());

  GlobalVariableToLocalMirrorMap ret;
  DenseMap<const Function *, DISubprogram *> FnMap;

  for (llvm::Function const &fn : Functions) {
    auto &blocks = fn.getBasicBlockList();
    if (!blocks.empty()) {
      auto &LocalMirror = ret[&fn];
      for (auto &block : blocks) {
        bool breakOut = false;
        for (auto &instruction : block) {
          if (auto const *DbgValue =
                  llvm::dyn_cast<llvm::DbgValueInst>(&instruction)) {
            auto *Variable = DbgValue->getVariable();
            if (Variable->getName().equals(LocalMirrorOfGlobalName)) {
              LocalMirror = Variable;
              breakOut = true;
              break;
            }
          }
          if (auto const *DbgDeclare =
                  llvm::dyn_cast<llvm::DbgDeclareInst>(&instruction)) {
            auto *Variable = DbgDeclare->getVariable();
            if (Variable->getName().equals(LocalMirrorOfGlobalName)) {
              LocalMirror = Variable;
              breakOut = true;
              break;
            }
          }
        }
        if (breakOut)
          break;
      }
      if (LocalMirror == nullptr) {
        // If we didn't find a dbg.value for any member of this
        // DIGlobalVariable, then no local mirror exists. We must manufacture
        // one.
        if (FnMap.empty()) {
          FnMap = makeSubprogramMap(M);
        }
        auto DIFn = FnMap[&fn];
        if (DIFn != nullptr) {
          const llvm::DITypeIdentifierMap EmptyMap;
          auto DIGVType = DIGV->getType().resolve(EmptyMap);
          DIBuilder DbgInfoBuilder(M);
          LocalMirror = DbgInfoBuilder.createLocalVariable(
              dwarf::DW_TAG_auto_variable, DIFn, LocalMirrorOfGlobalName,
              DIFn->getFile(), DIFn->getLine(), DIGVType);
        }
      }
    }
  }
  return ret;
}

// CheckedMulUInt64/CheckedAddUInt64 are small overflow-checked arithmetic
// helpers: they return false (leaving *Result unmodified) instead of
// silently wrapping when the operation would overflow uint64_t.
static bool CheckedMulUInt64(uint64_t LHS, uint64_t RHS, uint64_t *Result) {
  if (LHS != 0 && RHS > UINT64_MAX / LHS) {
    return false;
  }
  *Result = LHS * RHS;
  return true;
}

static bool CheckedAddUInt64(uint64_t LHS, uint64_t RHS, uint64_t *Result) {
  if (RHS > UINT64_MAX - LHS) {
    return false;
  }
  *Result = LHS + RHS;
  return true;
}

// PIX debug-transformation host-work budgets. These are NOT compiler,
// validator, or hardware limits -- shader semantics are entirely
// unaffected by them. A DISubrange-derived count/size pair that exceeds
// either budget below still describes a value that would compile and run
// correctly; this pass simply declines to eagerly expand it into
// individual per-element PIX debug records/IR, because doing so would
// cost this HOST PASS time and memory proportional to however large a
// (possibly debug-info-only, not independently verified against the real
// backing storage) count claims to be, which is unusable regardless of
// how internally self-consistent the numbers involved are.
//
// kMaxPixDebugEagerStorageBits bounds the total bit extent (element count
// times element size) this pass will eagerly expand for one array. 64KiB
// is a deliberately generous but finite policy choice for this pass's own
// internal work, not a language or hardware constant.
constexpr uint64_t kMaxPixDebugEagerStorageBits = 64ull * 1024 * 8;

// kMaxPixDebugEagerElementCount bounds the element COUNT independently of
// the bit-extent budget above. This is necessary because a zero or
// otherwise-unsupported per-element size would make count * elementSize
// trivially 0 (or otherwise small), trivially satisfying the bit-extent
// budget regardless of how enormous count itself is, letting an unbounded
// count bypass that budget entirely. Chosen as the bit-extent budget
// divided by the smallest scalar size this pass materializes debug values
// for (16 bits, e.g. min16float/half), so this element-count cap is never
// more permissive than the bit-extent budget for any real element size
// this pass actually supports.
constexpr uint64_t kMaxPixDebugEagerElementCount =
    kMaxPixDebugEagerStorageBits / 16;

// TryBoundEagerArrayWork validates that eagerly expanding Count elements of
// ElementSizeInBits each, starting at AccumulatedOffset, is work this pass
// is willing to actually perform. Beyond the uint64_t-overflow-safe
// arithmetic itself, this independently requires: (a) the resulting upper
// bound offset fit in this pass's own 32-bit OffsetInBits/SizeInBits
// representation (used throughout this file), and (b) both Count and the
// total bit extent stay within the PIX debug-transformation host-work
// budgets above, checked independently of one another so neither a huge
// count paired with a deceptively small/zero element size, nor a huge
// element size paired with a small count, can bypass the check meant to
// catch it. *OutExtentInBits/*OutUpperOffset are only set, and true
// returned, on full success.
static bool TryBoundEagerArrayWork(uint64_t Count, uint64_t ElementSizeInBits,
                                   uint64_t AccumulatedOffset,
                                   uint64_t *OutExtentInBits,
                                   uint64_t *OutUpperOffset) {
  if (Count > kMaxPixDebugEagerElementCount) {
    return false;
  }

  uint64_t ExtentInBits;
  uint64_t UpperOffset;
  if (!CheckedMulUInt64(Count, ElementSizeInBits, &ExtentInBits) ||
      !CheckedAddUInt64(AccumulatedOffset, ExtentInBits, &UpperOffset)) {
    return false;
  }

  if (UpperOffset > UINT32_MAX || ExtentInBits > kMaxPixDebugEagerStorageBits) {
    return false;
  }

  *OutExtentInBits = ExtentInBits;
  *OutUpperOffset = UpperOffset;
  return true;
}

// TryComputeArrayElementCount computes the total element count of a
// (possibly multi-dimensional) DXIL debug-info array type -- the product
// of every dimension's DISubrange::getCount(). DXC's own debug info for an
// array type is expected to contain nothing but DISubrange elements, one
// per dimension, so any other element kind, or no elements at all, is a
// shape this code does not know how to interpret safely. This also fails
// closed if any dimension's count is not strictly positive: DWARF uses -1
// as the "unknown/unbounded length" sentinel, and neither that nor an
// explicit 0 describes a real, iterable element count. This fails closed
// if multiplying the running product by the next dimension's count would
// overflow uint64_t, and -- independently of overflow -- if the final
// product exceeds UINT32_MAX. That bound is not arbitrary: it is this
// pass's own representation limit (OffsetInBits/SizeInBits, used
// throughout this file, are 32-bit `unsigned`), it matches DXIL's
// constant-index GEPs into a flattened array (an i32 operand, read back
// into a C++ `int` by handleStoreIfDestIsGlobal below), and it matches
// the sibling local/alloca path's own pre-existing `unsigned` element
// count. No legitimate backing array can exceed it, so a DISubrange
// product beyond it cannot correspond to real storage and must be
// rejected before any per-element allocation or loop, not merely before
// a later byte-size comparison -- otherwise a large-but-non-overflowing
// product (e.g. two dimensions whose product is a few billion) would
// still drive a per-element loop that is effectively a hang. *OutCount
// is only set, and true returned, when every dimension was checked
// successfully; on any failure *OutCount is left unmodified and the
// caller must not begin any allocation or loop keyed on it.
static bool TryComputeArrayElementCount(llvm::DICompositeType *ArrayTy,
                                        uint64_t *OutCount) {
  llvm::DINodeArray Elements = ArrayTy->getElements();
  if (Elements.size() == 0) {
    return false;
  }

  uint64_t Count = 1;
  for (llvm::DINode *Element : Elements) {
    llvm::DISubrange *Subrange = llvm::dyn_cast<llvm::DISubrange>(Element);
    if (Subrange == nullptr) {
      return false;
    }

    int64_t DimCount = Subrange->getCount();
    if (DimCount <= 0) {
      // Covers both an explicit empty/zero extent and DWARF's -1
      // "unknown length" sentinel.
      return false;
    }

    if (!CheckedMulUInt64(Count, static_cast<uint64_t>(DimCount), &Count)) {
      return false;
    }
  }

  if (Count > UINT32_MAX) {
    // See the function comment: no real backing array can be this large,
    // and continuing would drive a per-element loop of that many
    // iterations even though the product did not technically overflow
    // uint64_t.
    return false;
  }

  *OutCount = Count;
  return true;
}

std::vector<GlobalEmbeddedArrayElementStorage>
DescendTypeAndFindEmbeddedArrayElements(llvm::StringRef VariableName,
                                        uint64_t AccumulatedMemberOffset,
                                        llvm::DIType *Ty, uint64_t OffsetToSeek,
                                        uint64_t SizeToSeek) {
  const llvm::DITypeIdentifierMap EmptyMap;
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    auto BaseTy = DerivedTy->getBaseType().resolve(EmptyMap);
    auto storage = DescendTypeAndFindEmbeddedArrayElements(
        VariableName, AccumulatedMemberOffset, BaseTy, OffsetToSeek,
        SizeToSeek);
    if (!storage.empty()) {
      return storage;
    }
  } else if (auto *CompositeTy = llvm::dyn_cast<llvm::DICompositeType>(Ty)) {
    switch (CompositeTy->getTag()) {
    case llvm::dwarf::DW_TAG_array_type: {
      // DXC flattens a multi-dimensional array to a single one-dimensional
      // array in the module. The true array extent is the product of the
      // dimensions. Fail closed (no storage found for this array) rather
      // than compute an offset or iterate from an unsafe/overflowing
      // element count.
      uint64_t TotalElementCount = 0;
      if (!TryComputeArrayElementCount(CompositeTy, &TotalElementCount)) {
        break;
      }

      llvm::DIType *ElementTy = CompositeTy->getBaseType().resolve(EmptyMap);
      if (ElementTy == nullptr) {
        break;
      }

      if (llvm::DIBasicType *BasicTy =
              llvm::dyn_cast<llvm::DIBasicType>(ElementTy)) {
        // Use the shared eager-work-bounded check: beyond uint64_t-overflow
        // safety, this also requires the result fit in this pass's own
        // 32-bit OffsetInBits/SizeInBits representation (used for the two
        // fields this loop writes into below -- a count that survives a
        // plain uint64_t-overflow check can still, when multiplied by a
        // real element size, exceed what a 32-bit field can hold; e.g.
        // 134,217,729 32-bit elements is comfortably below UINT32_MAX on
        // its own, but its bit extent, 4,294,967,328, is not, and silently
        // truncating that into a 32-bit OffsetInBits below would alias to
        // the wrong bit position instead of merely being slow), and stay
        // within this pass's own eager-expansion host-work budgets, since
        // this loop must materialize one named record per element and so
        // cannot be made analytic the way the sibling branch below is.
        uint64_t ArrayExtentInBits;
        uint64_t UpperOffset;
        if (TryBoundEagerArrayWork(TotalElementCount, BasicTy->getSizeInBits(),
                                   AccumulatedMemberOffset, &ArrayExtentInBits,
                                   &UpperOffset)) {
          const bool CorrectLowerOffset =
              AccumulatedMemberOffset == OffsetToSeek;
          const bool CorrectUpperOffset =
              UpperOffset == OffsetToSeek + SizeToSeek;
          if (CorrectLowerOffset && CorrectUpperOffset) {
            std::vector<GlobalEmbeddedArrayElementStorage> storage;
            for (uint64_t i = 0; i < TotalElementCount; ++i) {
              // Safe: i < TotalElementCount, and TotalElementCount *
              // BasicTy->getSizeInBits() was already checked above, both for
              // uint64_t overflow and for fitting in OffsetInBits/SizeInBits.
              uint64_t ElementOffset =
                  AccumulatedMemberOffset + i * BasicTy->getSizeInBits();
              GlobalEmbeddedArrayElementStorage element;
              element.Name = VariableName.str() + "." + std::to_string(i);
              element.Offset = static_cast<OffsetInBits>(ElementOffset);
              element.Size = static_cast<SizeInBits>(BasicTy->getSizeInBits());
              storage.push_back(std::move(element));
            }
            return storage;
          }
        }
      }

      // The array's elements are themselves aggregates, so descend into
      // whichever single element could contain the sought offset. Every
      // caller of this function seeks the position of exactly one flattened
      // leaf variable, never a span covering more than one array element, so
      // at most one index can ever satisfy the search: compute it directly
      // instead of looping over -- and recursing into -- every element, which
      // would otherwise cost time proportional to however large a (possibly
      // untrustworthy, debug-info-supplied) element count claims to be. Still
      // uses the same shared bounded-work check as the sibling branch above
      // (rather than only an overflow/representability check) so this stays
      // consistent and equally fail-closed even though this branch itself no
      // longer loops.
      uint64_t DescendExtentInBits;
      uint64_t DescendUpperOffset;
      if (!TryBoundEagerArrayWork(TotalElementCount, ElementTy->getSizeInBits(),
                                  AccumulatedMemberOffset, &DescendExtentInBits,
                                  &DescendUpperOffset)) {
        break;
      }
      uint64_t ElementSizeInBits = ElementTy->getSizeInBits();
      uint64_t SoughtEnd;
      if (ElementSizeInBits != 0 && OffsetToSeek >= AccumulatedMemberOffset &&
          CheckedAddUInt64(OffsetToSeek, SizeToSeek, &SoughtEnd)) {
        uint64_t RelativeOffset = OffsetToSeek - AccumulatedMemberOffset;
        uint64_t CandidateIndex = RelativeOffset / ElementSizeInBits;
        if (CandidateIndex < TotalElementCount) {
          // Safe: CandidateIndex < TotalElementCount, and the product/sum
          // below is bounded above by DescendUpperOffset, already checked.
          uint64_t CandidateElementStart =
              AccumulatedMemberOffset + ElementSizeInBits * CandidateIndex;
          uint64_t CandidateElementEnd =
              CandidateElementStart + ElementSizeInBits;
          // The sought [OffsetToSeek, SoughtEnd) range must lie wholly
          // within this one candidate element -- not merely start within
          // it -- or this is not a match (and, per the comment above, no
          // other candidate could be one either).
          if (SoughtEnd <= CandidateElementEnd) {
            std::vector<GlobalEmbeddedArrayElementStorage> storage =
                DescendTypeAndFindEmbeddedArrayElements(
                    VariableName, CandidateElementStart, ElementTy,
                    OffsetToSeek, SizeToSeek);
            if (!storage.empty()) {
              return storage;
            }
          }
        }
      }
    } break;
    case llvm::dwarf::DW_TAG_structure_type:
    case llvm::dwarf::DW_TAG_class_type: {
      for (auto Element : CompositeTy->getElements()) {
        if (auto diMember = llvm::dyn_cast<DIType>(Element)) {
          auto storage = DescendTypeAndFindEmbeddedArrayElements(
              VariableName,
              AccumulatedMemberOffset + diMember->getOffsetInBits(), diMember,
              OffsetToSeek, SizeToSeek);
          if (!storage.empty()) {
            return storage;
          }
        }
      }
    } break;
    }
  }
  return {};
}

GlobalStorageMap GatherGlobalEmbeddedArrayStorage(llvm::Module &M) {
  GlobalStorageMap ret;
  auto DebugFinder = llvm::make_unique<llvm::DebugInfoFinder>();
  DebugFinder->processModule(M);
  auto GlobalVariables = DebugFinder->global_variables();

  // First find the list of global variables that represent HLSL global statics:
  const llvm::DITypeIdentifierMap EmptyMap;
  SmallVector<llvm::DIGlobalVariable *, 8> GlobalStaticVariables;
  for (llvm::DIGlobalVariable *DIGV : GlobalVariables) {
    if (DIGV->isLocalToUnit()) {
      llvm::DIType *DIGVType = DIGV->getType().resolve(EmptyMap);
      // We're only interested in aggregates, since only they might have
      // embedded arrays:
      if (isa<llvm::DICompositeType>(DIGVType)) {
        auto LocalMirrors = GenerateGlobalToLocalMirrorMap(M, DIGV);
        if (!LocalMirrors.empty()) {
          GlobalStaticVariables.push_back(DIGV);
          ret[DIGV].LocalMirrors = std::move(LocalMirrors);
        }
      }
    }
  }

  // Now find any globals that represent embedded arrays inside the global
  // statics
  for (auto HLSLStruct : GlobalStaticVariables) {
    for (llvm::DIGlobalVariable *DIGV : GlobalVariables) {
      if (DIGV != HLSLStruct && !DIGV->isLocalToUnit()) {
        llvm::DIType *DIGVType = DIGV->getType().resolve(EmptyMap);
        if (auto *DIGVDerivedType =
                llvm::dyn_cast<llvm::DIDerivedType>(DIGVType)) {
          if (DIGVDerivedType->getTag() == llvm::dwarf::DW_TAG_member) {
            // This type is embedded within the containing DIGSV type.
            // A flattened multi-dimensional array member renames the module
            // global but not the debug variable, so only the linkage name
            // still identifies it.
            llvm::StringRef GlobalName = DIGV->getLinkageName();
            if (GlobalName.empty()) {
              GlobalName = DIGV->getName();
            }
            const llvm::DITypeIdentifierMap EmptyMap;
            auto *Ty = HLSLStruct->getType().resolve(EmptyMap);
            auto Storage = DescendTypeAndFindEmbeddedArrayElements(
                GlobalName, 0, Ty, DIGVDerivedType->getOffsetInBits(),
                DIGVDerivedType->getSizeInBits());
            auto &ArrayStorage = ret[HLSLStruct].ArrayElementStorage;
            std::move(Storage.begin(), Storage.end(),
                      std::back_inserter(ArrayStorage));
          }
        }
      }
    }
  }
  return ret;
}

bool DxilDbgValueToDbgDeclare::runOnModule(llvm::Module &M) {
  auto GlobalEmbeddedArrayStorage = GatherGlobalEmbeddedArrayStorage(M);

  bool Changed = false;

  auto &Functions = M.getFunctionList();
  for (auto &fn : Functions) {
    llvm::SmallPtrSet<Value *, 16> RayQueryHandles;
    PIXPassHelpers::FindRayQueryHandlesForFunction(&fn, RayQueryHandles);
    // #DSLTodo: We probably need to merge the list of variables for each
    // export into one set so that WinPIX shader debugging can follow a
    // thread through any function within a given module. (Unless PIX
    // chooses to launch a new debugging session whenever control passes
    // from one function to another.) For now, it's sufficient to treat each
    // exported function as having completely separate variables by clearing
    // this member:
    m_Registers.clear();
    // Note: they key problem here is variables in common functions called
    // by multiple exported functions. The DILocalVariables in the common
    // function will be exactly the same objects no matter which export
    // called the common function, so the instrumentation here gets a bit
    // confused that the same variable is present in two functions and ends
    // up pointing one function to allocas in another function. (This is
    // easy to repro: comment out the above clear(), and run
    // PixTest::PixStructAnnotation_Lib_DualRaygen.) Not sure what the right
    // path forward is: might be that we have to tag m_Registers with the
    // exported function, and maybe write out a function identifier during
    // debug instrumentation...
    auto &blocks = fn.getBasicBlockList();
    if (!blocks.empty()) {
      for (auto &block : blocks) {
        std::vector<Instruction *> instructions;
        for (auto &instruction : block) {
          instructions.push_back(&instruction);
        }
        // Handle store instructions before handling dbg.value, since the
        // latter will add store instructions that we don't need to examine.
        // Why do we handle store instructions? It's for the case of
        // non-const global statics that are backed by an llvm global,
        // rather than an alloca. In the llvm global case, there is no
        // debug linkage between the store and the HLSL variable being
        // modified. But we can patch together enough knowledge about those
        // from the lists of such globals (HLSL and llvm) and comparing the
        // lists.
        for (auto &instruction : instructions) {
          if (auto *Store = llvm::dyn_cast<llvm::StoreInst>(instruction)) {
            // Preserve changes reported by every processed store.
            Changed |=
                handleStoreIfDestIsGlobal(M, GlobalEmbeddedArrayStorage, Store);
          }
        }
        for (auto &instruction : instructions) {
          if (auto *DbgValue =
                  llvm::dyn_cast<llvm::DbgValueInst>(instruction)) {
            llvm::Value *V = DbgValue->getValue();
            if (RayQueryHandles.count(V) != 0)
              continue;
            Changed = true;
            handleDbgValue(M, DbgValue);
            DbgValue->eraseFromParent();
          }
        }
      }
    }
  }
  return Changed;
}

static llvm::DIType *FindStructMemberTypeAtOffset(llvm::DICompositeType *Ty,
                                                  uint64_t Offset,
                                                  uint64_t Size);

static llvm::DIType *FindMemberTypeAtOffset(llvm::DIType *Ty, uint64_t Offset,
                                            uint64_t Size) {
  VALUE_TO_DECLARE_LOG("PopulateAllocaMap for type tag %d", Ty->getTag());
  const llvm::DITypeIdentifierMap EmptyMap;
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    switch (DerivedTy->getTag()) {
    default:
      assert(!"Unhandled DIDerivedType");
      return nullptr;
    case llvm::dwarf::DW_TAG_arg_variable: // "this" pointer
    case llvm::dwarf::DW_TAG_pointer_type: // "this" pointer
                                           // what to do here?
      return nullptr;
    case llvm::dwarf::DW_TAG_restrict_type:
    case llvm::dwarf::DW_TAG_reference_type:
    case llvm::dwarf::DW_TAG_const_type:
    case llvm::dwarf::DW_TAG_typedef:
      return FindMemberTypeAtOffset(DerivedTy->getBaseType().resolve(EmptyMap),
                                    Offset, Size);
    case llvm::dwarf::DW_TAG_member:
      return FindMemberTypeAtOffset(DerivedTy->getBaseType().resolve(EmptyMap),
                                    Offset, Size);
    case llvm::dwarf::DW_TAG_subroutine_type:
      // ignore member functions.
      return nullptr;
    }
  } else if (auto *CompositeTy = llvm::dyn_cast<llvm::DICompositeType>(Ty)) {
    switch (CompositeTy->getTag()) {
    default:
      assert(!"Unhandled DICompositeType");
      return nullptr;
    case llvm::dwarf::DW_TAG_array_type:
      return nullptr;
    case llvm::dwarf::DW_TAG_structure_type:
    case llvm::dwarf::DW_TAG_class_type:
      return FindStructMemberTypeAtOffset(CompositeTy, Offset, Size);
    case llvm::dwarf::DW_TAG_enumeration_type:
      return nullptr;
    }
  } else if (auto *BasicTy = llvm::dyn_cast<llvm::DIBasicType>(Ty)) {
    if (Offset == 0 && Ty->getSizeInBits() == Size) {
      return BasicTy;
    }
  }

  assert(!"Unhandled DIType");
  return nullptr;
}

// SortMembers traverses all of Ty's members and returns them sorted
// by their offset from Ty's start. Returns true if the function succeeds
// and false otherwise.
static bool
SortMembers(llvm::DICompositeType *Ty,
            std::map<OffsetInBits, llvm::DIDerivedType *> *SortedMembers) {
  auto Elements = Ty->getElements();
  if (Elements.begin() == Elements.end()) {
    return false;
  }
  for (auto *Element : Elements) {
    switch (Element->getTag()) {
    case llvm::dwarf::DW_TAG_member: {
      if (auto *Member = llvm::dyn_cast<llvm::DIDerivedType>(Element)) {
        if (Member->getSizeInBits()) {
          auto it = SortedMembers->emplace(
              std::make_pair(Member->getOffsetInBits(), Member));
          (void)it;
          assert(it.second &&
                 "Invalid DIStructType"
                 " - members with the same offset -- are unions possible?");
        }
        break;
      }
      assert(!"member is not a Member");
      return false;
    }
    case llvm::dwarf::DW_TAG_subprogram: {
      if (isa<llvm::DISubprogram>(Element)) {
        continue;
      }
      assert(!"DISubprogram not understood");
      return false;
    }
    case llvm::dwarf::DW_TAG_inheritance: {
      if (auto *Member = llvm::dyn_cast<llvm::DIDerivedType>(Element)) {
        auto it = SortedMembers->emplace(
            std::make_pair(Member->getOffsetInBits(), Member));
        (void)it;
        assert(it.second &&
               "Invalid DIStructType"
               " - members with the same offset -- are unions possible?");
      }
      continue;
    }
    default:
      assert(!"Unhandled field type in DIStructType");
      return false;
    }
  }
  return true;
}

static bool IsResourceObject(llvm::DIDerivedType *DT) {
  const llvm::DITypeIdentifierMap EmptyMap;
  auto *BT = DT->getBaseType().resolve(EmptyMap);
  if (auto *CompositeTy = llvm::dyn_cast<llvm::DICompositeType>(BT)) {
    // Resource variables (e.g. TextureCube) are composite types but have no
    // elements:
    if (CompositeTy->getElements().begin() ==
        CompositeTy->getElements().end()) {
      auto name = CompositeTy->getName();
      auto openTemplateListMarker = name.find_first_of('<');
      if (openTemplateListMarker != llvm::StringRef::npos) {
        auto hlslType = name.substr(0, openTemplateListMarker);
        for (int i = static_cast<int>(hlsl::DXIL::ResourceKind::Invalid) + 1;
             i < static_cast<int>(hlsl::DXIL::ResourceKind::NumEntries); ++i) {
          if (hlslType == hlsl::GetResourceKindName(
                              static_cast<hlsl::DXIL::ResourceKind>(i))) {
            return true;
          }
        }
      }
    }
  }
  return false;
}

static llvm::DIType *FindStructMemberTypeAtOffset(llvm::DICompositeType *Ty,
                                                  uint64_t Offset,
                                                  uint64_t Size) {
  std::map<OffsetInBits, llvm::DIDerivedType *> SortedMembers;
  if (!SortMembers(Ty, &SortedMembers)) {
    return Ty;
  }

  const llvm::DITypeIdentifierMap EmptyMap;

  for (auto &member : SortedMembers) {
    // "Inheritance" is a member of a composite type, but has size of zero.
    // Therefore, we must descend the hierarchy once to find an actual type.
    llvm::DIType *memberType = member.second;
    if (memberType->getTag() == llvm::dwarf::DW_TAG_inheritance) {
      memberType = member.second->getBaseType().resolve(EmptyMap);
    }
    if (Offset >= member.first &&
        Offset < member.first + memberType->getSizeInBits()) {
      uint64_t OffsetIntoThisType = Offset - member.first;
      return FindMemberTypeAtOffset(memberType, OffsetIntoThisType, Size);
    }
  }

  // Structure resources are expected to fail this (they have no real
  // meaning in storage)
  if (SortedMembers.size() == 1) {
    switch (SortedMembers.begin()->second->getTag()) {
    case llvm::dwarf::DW_TAG_structure_type:
    case llvm::dwarf::DW_TAG_class_type:
      if (IsResourceObject(SortedMembers.begin()->second)) {
        return nullptr;
      }
    }
  }
#ifdef VALUE_TO_DECLARE_LOGGING
  VALUE_TO_DECLARE_LOG(
      "Didn't find a member that straddles the sought type. Container:");
  {
    ScopedIndenter indent;
    Ty->dump();
    DumpFullType(Ty);
  }
  VALUE_TO_DECLARE_LOG(
      "Sought type is at offset %d size %d. Members and offsets:", Offset,
      Size);
  {
    ScopedIndenter indent;
    for (auto const &member : SortedMembers) {
      member.second->dump();
      LogPartialLine("Offset %d (size %d): ", member.first,
                     member.second->getSizeInBits());
      DumpFullType(member.second);
    }
  }
#endif
  assert(!"Didn't find a member that straddles the sought type");
  return nullptr;
}

static bool IsDITypePointer(DIType *DTy,
                            const llvm::DITypeIdentifierMap &EmptyMap) {
  DIDerivedType *DerivedTy = dyn_cast<DIDerivedType>(DTy);
  if (!DerivedTy)
    return false;
  switch (DerivedTy->getTag()) {
  case llvm::dwarf::DW_TAG_pointer_type:
    return true;
  case llvm::dwarf::DW_TAG_typedef:
  case llvm::dwarf::DW_TAG_const_type:
  case llvm::dwarf::DW_TAG_restrict_type:
  case llvm::dwarf::DW_TAG_reference_type:
    return IsDITypePointer(DerivedTy->getBaseType().resolve(EmptyMap),
                           EmptyMap);
  }
  return false;
}

void DxilDbgValueToDbgDeclare::handleDbgValue(llvm::Module &M,
                                              llvm::DbgValueInst *DbgValue) {
  VALUE_TO_DECLARE_LOG("DbgValue named %s", DbgValue->getName().str().c_str());

  llvm::DIVariable *Variable = DbgValue->getVariable();
  if (Variable != nullptr) {
    VALUE_TO_DECLARE_LOG("... DbgValue referred to variable named %s",
                         Variable->getName().str().c_str());
  } else {
    VALUE_TO_DECLARE_LOG("... variable was null too");
  }

  llvm::Value *ValueFromDbgInst = DbgValue->getValue();
  if (ValueFromDbgInst == nullptr) {
    // The metadata contained a null Value, so we ignore it. This
    // seems to be a dxcompiler bug.
    VALUE_TO_DECLARE_LOG("...Null value!");
    return;
  }

  const llvm::DITypeIdentifierMap EmptyMap;
  llvm::DIType *Ty = Variable->getType().resolve(EmptyMap);
  if (Ty == nullptr) {
    return;
  }

  if (llvm::isa<llvm::PointerType>(ValueFromDbgInst->getType())) {
    // Safeguard: If the type is not a pointer type, then this is
    // dbg.value directly pointing to a memory location instead of
    // a value.
    if (!IsDITypePointer(Ty, EmptyMap)) {
      // We only know how to handle AllocaInsts for now
      if (!isa<AllocaInst>(ValueFromDbgInst)) {
        VALUE_TO_DECLARE_LOG(
            "... variable had pointer type, but is not an alloca.");
        return;
      }

      IRBuilder<> B(DbgValue->getNextNode());
      ValueFromDbgInst = B.CreateLoad(ValueFromDbgInst);
    }
  }

  // Members' "base type" is actually the containing aggregate's type.
  // To find the actual type of the variable, we must descend the
  // container's type hierarchy to find the type at the expected
  // offset/size.
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    const llvm::DITypeIdentifierMap EmptyMap;
    switch (DerivedTy->getTag()) {
    case llvm::dwarf::DW_TAG_member: {
      Ty = FindMemberTypeAtOffset(DerivedTy->getBaseType().resolve(EmptyMap),
                                  DerivedTy->getOffsetInBits(),
                                  DerivedTy->getSizeInBits());
      if (Ty == nullptr) {
        return;
      }
    } break;
    }
  }

  auto &Register = m_Registers[Variable];
  if (Register == nullptr) {
    Register.reset(new VariableRegisters(
        DbgValue->getDebugLoc(),
        DbgValue->getParent()->getParent()->getEntryBlock().begin(), Variable,
        Ty, &M));
  }

  // Convert the offset from DbgValue's expression to a packed
  // offset, which we'll need in order to determine the (packed)
  // offset of each scalar Value in DbgValue.
  llvm::DIExpression *expression = DbgValue->getExpression();
  const OffsetInBits AlignedOffsetFromVar =
      GetAlignedOffsetFromDIExpression(expression);
  OffsetInBits PackedOffsetFromVar;
  const OffsetManager &Offsets = Register->GetOffsetManager();
  if (!Offsets.GetPackedOffsetFromAlignedOffset(AlignedOffsetFromVar,
                                                &PackedOffsetFromVar)) {
    // todo: output geometry for GS
    return;
  }

  const OffsetInBits InitialOffset = PackedOffsetFromVar;
  auto *insertPt = llvm::dyn_cast<llvm::Instruction>(ValueFromDbgInst);
  if (insertPt == nullptr) {
    // Constants and arguments are available at the dbg.value location.
    insertPt = DbgValue;
  }
  if (insertPt != nullptr && !llvm::isa<TerminatorInst>(insertPt)) {
    insertPt = insertPt->getNextNode();
    // Drivers may crash if phi nodes aren't always at the top of a block,
    // so we must skip over them before inserting instructions.
    while (llvm::isa<llvm::PHINode>(insertPt)) {
      insertPt = insertPt->getNextNode();
    }

    if (insertPt != nullptr) {
      llvm::IRBuilder<> B(insertPt);
      B.SetCurrentDebugLocation(llvm::DebugLoc());

      auto *Zero = B.getInt32(0);

      // Now traverse a list of pairs {Scalar Value, InitialOffset +
      // Offset}. InitialOffset is the offset from DbgValue's expression
      // (i.e., the offset from the Variable's start), and Offset is the
      // Scalar Value's packed offset from DbgValue's value.
      for (const ValueAndOffset &VO :
           SplitValue(ValueFromDbgInst, InitialOffset, B)) {

        OffsetInBits AlignedOffset;
        if (!Offsets.GetAlignedOffsetFromPackedOffset(VO.m_PackedOffset,
                                                      &AlignedOffset)) {
          continue;
        }

        auto *AllocaInst = Register->GetRegisterForAlignedOffset(AlignedOffset);
        if (AllocaInst == nullptr) {
          assert(!"Failed to find alloca for var[offset]");
          continue;
        }

        llvm::Type *ShadowElementType =
            AllocaInst->getAllocatedType()->getArrayElementType();
        llvm::Value *ValueToStore = VO.m_V;
        if (ShadowElementType != ValueToStore->getType()) {
          // Emit a bitcast to match the shadow alloca element type when the
          // shader reinterprets the bits without converting them.
          const llvm::DataLayout &DataLayout = M.getDataLayout();
          const bool SameWidth =
              !ShadowElementType->isAggregateType() &&
              !ValueToStore->getType()->isAggregateType() &&
              !ShadowElementType->isPointerTy() &&
              !ValueToStore->getType()->isPointerTy() &&
              DataLayout.getTypeSizeInBits(ShadowElementType) ==
                  DataLayout.getTypeSizeInBits(ValueToStore->getType());
          if (!SameWidth) {
            continue;
          }
          ValueToStore = B.CreateBitCast(ValueToStore, ShadowElementType);
        }

        llvm::Value *GEP = B.CreateGEP(AllocaInst, {Zero, Zero});
        B.CreateStore(ValueToStore, GEP);
      }
    }
  }
}

struct GlobalVariableAndStorage {
  llvm::DIGlobalVariable *DIGV;
  OffsetInBits Offset;
};

GlobalVariableAndStorage
GetOffsetFromGlobalVariable(llvm::StringRef name,
                            GlobalStorageMap &GlobalEmbeddedArrayStorage) {
  GlobalVariableAndStorage ret{};
  for (auto &Variable : GlobalEmbeddedArrayStorage) {
    for (auto &Storage : Variable.second.ArrayElementStorage) {
      if (llvm::StringRef(Storage.Name).equals(name)) {
        ret.DIGV = Variable.first;
        ret.Offset = Storage.Offset;
        return ret;
      }
    }
  }
  return ret;
}

bool DxilDbgValueToDbgDeclare::handleStoreIfDestIsGlobal(
    llvm::Module &M, GlobalStorageMap &GlobalEmbeddedArrayStorage,
    llvm::StoreInst *Store) {
  if (Store->getDebugLoc()) {
    llvm::Value *V = Store->getPointerOperand();
    std::string MemberName;
    if (auto *Constant = llvm::dyn_cast<llvm::ConstantExpr>(V)) {
      ScopedInstruction asInstr(Constant->getAsInstruction());
      if (auto *asGEP =
              llvm::dyn_cast<llvm::GetElementPtrInst>(asInstr.Get())) {
        // We are only interested in the case of basic types within an array
        // because the PIX debug instrumentation operates at that level.
        // Aggregate members will have been descended through to produce
        // their own entries in the GlobalStorageMap. Consequently, we're
        // only interested in the GEP's index into the array. Any deeper
        // indexing in the GEP will be for embedded aggregates. The three
        // operands in such a GEP mean:
        //    0 = the pointer
        //    1 = dereference the pointer (expected to be constant int zero)
        //    2 = the index into the array
        if (asGEP->getNumOperands() == 3 &&
            llvm::isa<ConstantInt>(asGEP->getOperand(1)) &&
            llvm::dyn_cast<ConstantInt>(asGEP->getOperand(1))
                    ->getLimitedValue() == 0) {
          // TODO: The case where this index is not a constant int
          // (Needs changes to the allocas generated elsewhere in this
          // pass.)
          if (auto *arrayIndexAsConstInt =
                  llvm::dyn_cast<ConstantInt>(asGEP->getOperand(2))) {
            int MemberIndex = arrayIndexAsConstInt->getLimitedValue();
            MemberName = std::string(asGEP->getPointerOperand()->getName()) +
                         "." + std::to_string(MemberIndex);
          }
        }
      }
    } else {
      MemberName = V->getName();
    }
    if (!MemberName.empty()) {
      auto Storage =
          GetOffsetFromGlobalVariable(MemberName, GlobalEmbeddedArrayStorage);
      if (Storage.DIGV != nullptr) {
        llvm::DILocalVariable *Variable =
            GlobalEmbeddedArrayStorage[Storage.DIGV]
                .LocalMirrors[Store->getParent()->getParent()];
        if (Variable != nullptr) {
          const llvm::DITypeIdentifierMap EmptyMap;
          llvm::DIType *Ty = Variable->getType().resolve(EmptyMap);
          if (Ty != nullptr) {
            auto &Register = m_Registers[Variable];
            if (Register == nullptr) {
              Register.reset(new VariableRegisters(
                  Store->getDebugLoc(),
                  Store->getParent()->getParent()->getEntryBlock().begin(),
                  Variable, Ty, &M));
            }
            auto *AllocaInst =
                Register->GetRegisterForAlignedOffset(Storage.Offset);
            if (AllocaInst != nullptr) {
              IRBuilder<> B(Store->getNextNode());
              auto *Zero = B.getInt32(0);
              auto *GEP = B.CreateGEP(AllocaInst, {Zero, Zero});
              B.CreateStore(Store->getValueOperand(), GEP);
              return true; // yes, we modified the module
            }
          }
        }
      }
    }
  }
  return false; // no we did not modify the module
}

SizeInBits VariableRegisters::GetVariableSizeInbits(DIVariable *Var) {
  const llvm::DITypeIdentifierMap EmptyMap;
  DIType *Ty = Var->getType().resolve(EmptyMap);
  DIDerivedType *DerivedTy = nullptr;
  if (BaseTypeIfItIsBasicAndLarger(Ty))
    return Ty->getSizeInBits();
  while (Ty && (Ty->getSizeInBits() == 0 &&
                (DerivedTy = dyn_cast<DIDerivedType>(Ty)))) {
    Ty = DerivedTy->getBaseType().resolve(EmptyMap);
  }

  if (!Ty) {
    assert(false &&
           "Unexpected inability to resolve base type with a real size.");
    return 0;
  }
  return Ty->getSizeInBits();
}

llvm::AllocaInst *
VariableRegisters::GetRegisterForAlignedOffset(OffsetInBits Offset) const {
  auto it = m_AlignedOffsetToAlloca.find(Offset);
  if (it == m_AlignedOffsetToAlloca.end()) {
    return nullptr;
  }
  return it->second;
}

VariableRegisters::VariableRegisters(
    llvm::DebugLoc const &dbgLoc,
    llvm::BasicBlock::iterator allocaInsertionPoint, llvm::DIVariable *Variable,
    llvm::DIType *Ty, llvm::Module *M)
    : m_dbgLoc(dbgLoc), m_Variable(Variable), m_B(allocaInsertionPoint),
      m_DbgDeclareFn(
          llvm::Intrinsic::getDeclaration(M, llvm::Intrinsic::dbg_declare)) {
  PopulateAllocaMap(Ty);
  m_Offsets.AlignTo(Ty); // For padding.

  // (min16* types can occupy 16 or 32 bits depending on whether or not they
  // are natively supported. If non-native, the alignment will be 32, but
  // the claimed size will still be 16, hence the "max" here)
  assert(m_Offsets.GetCurrentAlignedOffset() ==
         std::max<uint64_t>(DITypePeelTypeAlias(Ty)->getSizeInBits(),
                            DITypePeelTypeAlias(Ty)->getAlignInBits()));
}

void VariableRegisters::PopulateAllocaMap(llvm::DIType *Ty) {
  VALUE_TO_DECLARE_LOG("PopulateAllocaMap for type tag %d", Ty->getTag());
  const llvm::DITypeIdentifierMap EmptyMap;
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    switch (DerivedTy->getTag()) {
    default:
      assert(!"Unhandled DIDerivedType");
      m_Offsets.AlignToAndAddUnhandledType(DerivedTy);
      return;
    case llvm::dwarf::DW_TAG_arg_variable: // "this" pointer
    case llvm::dwarf::DW_TAG_pointer_type: // "this" pointer
    case llvm::dwarf::DW_TAG_restrict_type:
    case llvm::dwarf::DW_TAG_reference_type:
    case llvm::dwarf::DW_TAG_const_type:
    case llvm::dwarf::DW_TAG_typedef:
      PopulateAllocaMap(DerivedTy->getBaseType().resolve(EmptyMap));
      return;
    case llvm::dwarf::DW_TAG_member:
      if (auto *baseType = BaseTypeIfItIsBasicAndLarger(DerivedTy))
        PopulateAllocaMap_BasicType(baseType, DerivedTy->getSizeInBits());
      else
        PopulateAllocaMap(DerivedTy->getBaseType().resolve(EmptyMap));
      return;
    case llvm::dwarf::DW_TAG_subroutine_type:
      // ignore member functions.
      return;
    }
  } else if (auto *CompositeTy = llvm::dyn_cast<llvm::DICompositeType>(Ty)) {
    switch (CompositeTy->getTag()) {
    default:
      assert(!"Unhandled DICompositeType");
      m_Offsets.AlignToAndAddUnhandledType(CompositeTy);
      return;
    case llvm::dwarf::DW_TAG_array_type:
      PopulateAllocaMap_ArrayType(CompositeTy);
      return;
    case llvm::dwarf::DW_TAG_structure_type:
    case llvm::dwarf::DW_TAG_class_type:
      PopulateAllocaMap_StructType(CompositeTy);
      return;
    case llvm::dwarf::DW_TAG_enumeration_type: {
      auto *baseType = CompositeTy->getBaseType().resolve(EmptyMap);
      if (baseType != nullptr) {
        const OffsetInBits EnumerationStart =
            m_Offsets.GetCurrentAlignedOffset();
        PopulateAllocaMap(baseType);
        // Advance to the enumeration's own declared size.
        m_Offsets.AdvanceAlignedOffsetTo(
            EnumerationStart +
            static_cast<SizeInBits>(CompositeTy->getSizeInBits()));
      } else {
        m_Offsets.AlignToAndAddUnhandledType(CompositeTy);
      }
    }
      return;
    }
  } else if (auto *BasicTy = llvm::dyn_cast<llvm::DIBasicType>(Ty)) {
    PopulateAllocaMap_BasicType(BasicTy, 0 /*no size override*/);
    return;
  }

  assert(!"Unhandled DIType");
  m_Offsets.AlignToAndAddUnhandledType(Ty);
}

static llvm::Type *GetLLVMTypeFromDIBasicType(llvm::IRBuilder<> &B,
                                              llvm::DIBasicType *Ty) {
  const SizeInBits Size = Ty->getSizeInBits();

  switch (Ty->getEncoding()) {
  default:
    break;

  case llvm::dwarf::DW_ATE_boolean:
  case llvm::dwarf::DW_ATE_signed:
  case llvm::dwarf::DW_ATE_unsigned:
    switch (Size) {
    case 16:
      return B.getInt16Ty();
    case 32:
      return B.getInt32Ty();
    case 64:
      return B.getInt64Ty();
    }
    break;
  case llvm::dwarf::DW_ATE_float:
    switch (Size) {
    case 16:
      return B.getHalfTy();
    case 32:
      return B.getFloatTy();
    case 64:
      return B.getDoubleTy();
    }
    break;
  }

  return nullptr;
}

void VariableRegisters::PopulateAllocaMap_BasicType(llvm::DIBasicType *Ty,
                                                    unsigned sizeOverride) {
  llvm::Type *AllocaElementTy = GetLLVMTypeFromDIBasicType(m_B, Ty);
  assert(AllocaElementTy != nullptr);
  if (AllocaElementTy == nullptr) {
    return;
  }

  const auto offsets = m_Offsets.Add(Ty, sizeOverride);

  llvm::Type *AllocaTy = llvm::ArrayType::get(AllocaElementTy, 1);
  llvm::AllocaInst *&Alloca = m_AlignedOffsetToAlloca[offsets.Aligned];
  if (Alloca == nullptr) {
    Alloca = m_B.CreateAlloca(AllocaTy, m_B.getInt32(0));
    Alloca->setDebugLoc(llvm::DebugLoc());
  }

  auto *Storage = GetMetadataAsValue(llvm::ValueAsMetadata::get(Alloca));
  auto *Variable = GetMetadataAsValue(m_Variable);
  // Describe the aligned offset in the bit_piece so it agrees with the
  // debug-info field's declared offset.
  llvm::Value *Expression = GetMetadataAsValue(GetDIExpression(
      Ty, offsets.Aligned, GetVariableSizeInbits(m_Variable), sizeOverride));
  auto *DbgDeclare =
      m_B.CreateCall(m_DbgDeclareFn, {Storage, Variable, Expression});
  DbgDeclare->setDebugLoc(m_dbgLoc);
}

// NumArrayElements is a thin adapter over the shared, uint64_t-safe
// TryComputeArrayElementCount for this call site's existing `unsigned`
// (32-bit) element-count API: it fails closed (returning 0, this
// function's existing "unhandled" sentinel) for every shape
// TryComputeArrayElementCount itself rejects. TryComputeArrayElementCount
// already guarantees any count it returns fits in 32 bits, so the
// narrowing cast below is safe.
static unsigned NumArrayElements(llvm::DICompositeType *Array) {
  uint64_t Count = 0;
  if (!TryComputeArrayElementCount(Array, &Count)) {
    return 0;
  }
  return static_cast<unsigned>(Count);
}

void VariableRegisters::PopulateAllocaMap_ArrayType(llvm::DICompositeType *Ty) {
  unsigned NumElements = NumArrayElements(Ty);
  if (NumElements == 0) {
    m_Offsets.AlignToAndAddUnhandledType(Ty);
    return;
  }

  const SizeInBits ArraySizeInBits = Ty->getSizeInBits();

  const llvm::DITypeIdentifierMap EmptyMap;
  llvm::DIType *ElementTy = Ty->getBaseType().resolve(EmptyMap);
  if (ElementTy == nullptr) {
    m_Offsets.AlignToAndAddUnhandledType(Ty);
    return;
  }

  // This was previously only an assert -- compiled out entirely in a
  // release build, so it provided no protection there -- checking that
  // NumElements evenly divides the array's own declared total size.
  // Preserved exactly as originally written (rather than tightened to an
  // exact NumElements * ElementSizeInBits equality) because a real,
  // legitimate array of elements whose own unpadded size does not equal
  // their aligned in-array stride (e.g. an array of odd-sized structs each
  // padded up to their alignment, which the loop below accounts for via
  // AlignTo on every iteration) can have ArraySizeInBits be a multiple of
  // NumElements without being a multiple of ElementTy->getSizeInBits()
  // alone; tightening the check risks rejecting that legitimate shape.
  // Independently -- and this is the part genuinely new here --
  // TryBoundEagerArrayWork bounds this loop's own host work: NumElements
  // survived TryComputeArrayElementCount's own cap already, but a huge
  // count paired with a real (nonzero) element size can still describe
  // more per-element work (each iteration calls PopulateAllocaMap, which
  // is not O(1)) than this pass is willing to eagerly perform, independent
  // of whether the size-divisibility check above it passes.
  uint64_t ElementSizeInBits = ElementTy->getSizeInBits();
  uint64_t ExtentInBits;
  uint64_t UpperOffset;
  if (ArraySizeInBits % NumElements != 0 ||
      !TryBoundEagerArrayWork(NumElements, ElementSizeInBits, 0, &ExtentInBits,
                              &UpperOffset)) {
    m_Offsets.AlignToAndAddUnhandledType(Ty);
    return;
  }

  // After aligning the current aligned offset to ElementTy's natural
  // alignment, the current aligned offset must match Ty's offset
  // in bits.
  m_Offsets.AlignTo(ElementTy);

  const OffsetInBits ArrayStart = m_Offsets.GetCurrentAlignedOffset();

  for (unsigned i = 0; i < NumElements; ++i) {
    // This is only needed if ElementTy's size is not a multiple of
    // its natural alignment.
    m_Offsets.AlignTo(ElementTy);
    PopulateAllocaMap(ElementTy);
  }

  // The elements only account for the bits they occupy, which stops short
  // of the array's real end for a padded element type. Advance to the end.
  m_Offsets.AdvanceAlignedOffsetTo(ArrayStart + ArraySizeInBits);
}

void VariableRegisters::PopulateAllocaMap_StructType(
    llvm::DICompositeType *Ty) {
  VALUE_TO_DECLARE_LOG("Struct type : %s, size %d", Ty->getName().str().c_str(),
                       Ty->getSizeInBits());
  const SizeInBits StructSizeInBits = Ty->getSizeInBits();
  std::map<OffsetInBits, llvm::DIDerivedType *> SortedMembers;
  if (!SortMembers(Ty, &SortedMembers)) {
    m_Offsets.AlignToAndAddUnhandledType(Ty);
    return;
  }

  m_Offsets.AlignTo(Ty);
  const OffsetInBits StructStart = m_Offsets.GetCurrentAlignedOffset();
  const llvm::DITypeIdentifierMap EmptyMap;

  for (auto OffsetAndMember : SortedMembers) {
    VALUE_TO_DECLARE_LOG("Member: %s at packed offset %d",
                         OffsetAndMember.second->getName().str().c_str(),
                         OffsetAndMember.first);
    // Align the offsets to the member's type natural alignment. This
    // should always result in the current aligned offset being the
    // same as the member's offset.
    m_Offsets.AlignTo(OffsetAndMember.second);
    if (BaseTypeIfItIsBasicAndLarger(OffsetAndMember.second)) {
      // This is the bitfields case (i.e. a field that is smaller
      // than the type in which it resides). If we were to take
      // the base type, then the information about the member's
      // size would be lost
      //
      // The AlignTo above is a no-op for a bitfield, so snap to the declared
      // offset here to ensure it aligns with the debug info.
      m_Offsets.AdvanceAlignedOffsetTo(StructStart + OffsetAndMember.first);
      PopulateAllocaMap(OffsetAndMember.second);
    } else {
      if (OffsetAndMember.second->getAlignInBits() ==
          OffsetAndMember.second->getSizeInBits()) {
        assert(m_Offsets.GetCurrentAlignedOffset() ==
                   StructStart + OffsetAndMember.first &&
               "Offset mismatch in DIStructType");
      }
      if (IsResourceObject(OffsetAndMember.second)) {
        m_Offsets.AddResourceType(OffsetAndMember.second);
      } else {
        PopulateAllocaMap(
            OffsetAndMember.second->getBaseType().resolve(EmptyMap));
      }
    }
  }

  // The members between them only account for the bits they occupy, which stops
  // short of the struct's real end whenever the struct's alignment requires
  // tail padding. Advance to the struct's full size.
  m_Offsets.AdvanceAlignedOffsetTo(StructStart + StructSizeInBits);
}

// HLSL Change: remove unused function
#if 0
llvm::DILocation *VariableRegisters::GetVariableLocation() const
{
  const unsigned DefaultColumn = 1;
  return llvm::DILocation::get(
      m_B.getContext(),
      m_Variable->getLine(),
      DefaultColumn,
      m_Variable->getScope());
}
#endif

llvm::Value *VariableRegisters::GetMetadataAsValue(llvm::Metadata *M) const {
  return llvm::MetadataAsValue::get(m_B.getContext(), M);
}

llvm::DIExpression *
VariableRegisters::GetDIExpression(llvm::DIType *Ty, OffsetInBits Offset,
                                   SizeInBits ParentSize,
                                   unsigned sizeOverride) const {
  llvm::SmallVector<uint64_t, 3> ExpElements;
  if (Offset != 0 || Ty->getSizeInBits() != ParentSize) {
    ExpElements.emplace_back(llvm::dwarf::DW_OP_bit_piece);
    ExpElements.emplace_back(Offset);
    ExpElements.emplace_back(sizeOverride != 0 ? sizeOverride
                                               : Ty->getSizeInBits());
  }
  return llvm::DIExpression::get(m_B.getContext(), ExpElements);
}

using namespace llvm;

INITIALIZE_PASS(DxilDbgValueToDbgDeclare, DEBUG_TYPE,
                "Converts calls to dbg.value to dbg.declare + stores to new "
                "virtual registers",
                false, false)

ModulePass *llvm::createDxilDbgValueToDbgDeclarePass() {
  return new DxilDbgValueToDbgDeclare();
}
