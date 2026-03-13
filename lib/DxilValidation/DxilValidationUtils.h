///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// DxilValidationUttils.h                                                    //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// This file provides utils for validating DXIL.                             //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#pragma once

#include "dxc/DXIL/DxilConstants.h"
#include "dxc/DXIL/DxilResourceProperties.h"

#include "llvm/ADT/ArrayRef.h"
#include "llvm/ADT/StringRef.h"
#include "llvm/Analysis/CallGraph.h"
#include "llvm/IR/DebugLoc.h"
#include "llvm/IR/ModuleSlotTracker.h"

#include <memory>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace llvm;

namespace llvm {
class Module;
class Function;
class DataLayout;
class Metadata;
class Value;
class GlobalVariable;
class Instruction;
class Type;
} // namespace llvm

namespace hlsl {

///////////////////////////////////////////////////////////////////////////////
// Validation rules.
#include "DxilValidation.inc"

const char *GetValidationRuleText(ValidationRule value);

class DxilEntryProps;
class DxilModule;
class DxilResourceBase;
class DxilSignatureElement;

// Save status like output write for entries.
struct EntryStatus {
  bool HasOutputPosition[DXIL::kNumOutputStreams];
  unsigned OutputPositionMask[DXIL::kNumOutputStreams];
  std::vector<unsigned> OutputCols;
  std::vector<unsigned> PatchConstOrPrimCols;
  bool m_bCoverageIn, m_bInnerCoverageIn;
  bool HasViewID;
  unsigned DomainLocSize;
  EntryStatus(DxilEntryProps &EntryProps);
};

struct ValidationContext {
  bool Failed = false;
  Module &M;
  Module *DebugModule;
  DxilModule &DxilMod;
  const Type *HandleTy;
  const DataLayout &DL;
  DebugLoc LastDebugLocEmit;
  ValidationRule LastRuleEmit;
  std::unordered_set<Function *> EntryFuncCallSet;
  std::unordered_set<Function *> PatchConstFuncCallSet;
  std::unordered_map<unsigned, bool> UavCounterIncMap;
  std::unordered_map<Value *, unsigned> HandleResIndexMap;
  // TODO: save resource map for each createHandle/createHandleForLib.
  std::unordered_map<Value *, DxilResourceProperties> ResPropMap;
  std::unordered_map<Function *, std::vector<Function *>> PatchConstantFuncMap;
  std::unordered_map<Function *, std::unique_ptr<EntryStatus>> EntryStatusMap;
  bool IsLibProfile;
  const unsigned kDxilControlFlowHintMDKind;
  const unsigned kDxilPreciseMDKind;
  const unsigned kDxilNonUniformMDKind;
  const unsigned kLLVMLoopMDKind;
  unsigned m_DxilMajor, m_DxilMinor;
  ModuleSlotTracker SlotTracker;
  std::unique_ptr<CallGraph> CG;

  ValidationContext(Module &LLVMModule, Module *DebugModule,
                    DxilModule &DxilModule);

  void PropagateResMap(Value *V, DxilResourceBase *Res);
  void BuildResMap();
  bool HasEntryStatus(Function *F);
  EntryStatus &GetEntryStatus(Function *F);
  CallGraph &GetCallGraph();
  DxilResourceProperties GetResourceFromVal(Value *ResVal);

  void EmitGlobalVariableFormatError(GlobalVariable *GV, ValidationRule Rule,
                                     ArrayRef<StringRef> Args);
  // This is the least desirable mechanism, as it has no context.
  void EmitError(ValidationRule Rule);

  void FormatRuleText(std::string &RuleText, ArrayRef<StringRef> Args);
  void EmitFormatError(ValidationRule Rule, ArrayRef<StringRef> Args);

  void EmitMetaError(Metadata *Meta, ValidationRule Rule);

  // Use this instead of DxilResourceBase::GetGlobalName
  std::string GetResourceName(const hlsl::DxilResourceBase *Res);

  void EmitResourceError(const hlsl::DxilResourceBase *Res,
                         ValidationRule Rule);

  void EmitResourceFormatError(const hlsl::DxilResourceBase *Res,
                               ValidationRule Rule, ArrayRef<StringRef> Args);

  bool IsDebugFunctionCall(Instruction *I);

  Instruction *GetDebugInstr(Instruction *I);

  // Emit Error or note on instruction `I` with `Msg`.
  // If `IsError` is true, `Rule` may omit repeated errors
  void EmitInstrDiagMsg(Instruction *I, ValidationRule Rule, std::string Msg,
                        bool IsError = true);
  void EmitInstrError(Instruction *I, ValidationRule Rule);

  void EmitInstrNote(Instruction *I, std::string Msg);

  void EmitInstrFormatError(Instruction *I, ValidationRule Rule,
                            ArrayRef<StringRef> Args);

  void EmitSignatureError(DxilSignatureElement *SE, ValidationRule Rule);

  void EmitTypeError(Type *Ty, ValidationRule Rule);

  void EmitFnError(Function *F, ValidationRule Rule);

  void EmitFnFormatError(Function *F, ValidationRule Rule,
                         ArrayRef<StringRef> Args);

  void EmitFnAttributeError(Function *F, StringRef Kind, StringRef Value);
};

uint32_t ValidateDxilModule(llvm::Module *pModule, llvm::Module *pDebugModule);
} // namespace hlsl
