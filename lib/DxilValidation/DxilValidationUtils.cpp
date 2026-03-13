///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// DxilValidationUttils.cpp                                                  //
// Copyright (C) Microsoft Corporation. All rights reserved.                 //
// This file is distributed under the University of Illinois Open Source     //
// License. See LICENSE.TXT for details.                                     //
//                                                                           //
// This file provides utils for validating DXIL.                             //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include "DxilValidationUtils.h"

#include "dxc/DXIL/DxilEntryProps.h"
#include "dxc/DXIL/DxilInstructions.h"
#include "dxc/DXIL/DxilModule.h"
#include "dxc/DXIL/DxilOperations.h"
#include "dxc/DXIL/DxilUtil.h"
#include "dxc/Support/Global.h"

#include "llvm/IR/InstIterator.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Operator.h"
#include "llvm/Support/raw_ostream.h"

namespace hlsl {
EntryStatus::EntryStatus(DxilEntryProps &EntryProps)
    : m_bCoverageIn(false), m_bInnerCoverageIn(false), HasViewID(false) {
  for (unsigned I = 0; I < DXIL::kNumOutputStreams; I++) {
    HasOutputPosition[I] = false;
    OutputPositionMask[I] = 0;
  }

  OutputCols.resize(EntryProps.sig.OutputSignature.GetElements().size(), 0);
  PatchConstOrPrimCols.resize(
      EntryProps.sig.PatchConstOrPrimSignature.GetElements().size(), 0);
}

ValidationContext::ValidationContext(Module &LLVMModule, Module *DebugModule,
                                     DxilModule &DxilModule)
    : M(LLVMModule), DebugModule(DebugModule), DxilMod(DxilModule),
      DL(LLVMModule.getDataLayout()), LastRuleEmit((ValidationRule)-1),
      kDxilControlFlowHintMDKind(LLVMModule.getContext().getMDKindID(
          DxilMDHelper::kDxilControlFlowHintMDName)),
      kDxilPreciseMDKind(LLVMModule.getContext().getMDKindID(
          DxilMDHelper::kDxilPreciseAttributeMDName)),
      kDxilNonUniformMDKind(LLVMModule.getContext().getMDKindID(
          DxilMDHelper::kDxilNonUniformAttributeMDName)),
      kLLVMLoopMDKind(LLVMModule.getContext().getMDKindID("llvm.loop")),
      SlotTracker(&LLVMModule, true) {
  DxilMod.GetDxilVersion(m_DxilMajor, m_DxilMinor);
  HandleTy = DxilMod.GetOP()->GetHandleType();

  for (Function &F : LLVMModule.functions()) {
    if (DxilMod.HasDxilEntryProps(&F)) {
      DxilEntryProps &EntryProps = DxilMod.GetDxilEntryProps(&F);
      EntryStatusMap[&F] = llvm::make_unique<EntryStatus>(EntryProps);
    }
  }

  IsLibProfile = DxilModule.GetShaderModel()->IsLib();
  BuildResMap();
  // Collect patch constant map.
  if (IsLibProfile) {
    for (Function &F : DxilModule.GetModule()->functions()) {
      if (DxilModule.HasDxilEntryProps(&F)) {
        DxilEntryProps &EntryProps = DxilModule.GetDxilEntryProps(&F);
        DxilFunctionProps &Props = EntryProps.props;
        if (Props.IsHS()) {
          PatchConstantFuncMap[Props.ShaderProps.HS.patchConstantFunc]
              .emplace_back(&F);
        }
      }
    }
  } else {
    Function *Entry = DxilModule.GetEntryFunction();
    if (!DxilModule.HasDxilEntryProps(Entry)) {
      // must have props.
      EmitFnError(Entry, ValidationRule::MetaNoEntryPropsForEntry);
      return;
    }
    DxilEntryProps &EntryProps = DxilModule.GetDxilEntryProps(Entry);
    DxilFunctionProps &Props = EntryProps.props;
    if (Props.IsHS()) {
      PatchConstantFuncMap[Props.ShaderProps.HS.patchConstantFunc].emplace_back(
          Entry);
    }
  }
}

void ValidationContext::PropagateResMap(Value *V, DxilResourceBase *Res) {
  auto It = ResPropMap.find(V);
  if (It != ResPropMap.end()) {
    DxilResourceProperties RP = resource_helper::loadPropsFromResourceBase(Res);
    DxilResourceProperties ItRP = It->second;
    if (ItRP != RP) {
      EmitResourceError(Res, ValidationRule::InstrResourceMapToSingleEntry);
    }
  } else {
    DxilResourceProperties RP = resource_helper::loadPropsFromResourceBase(Res);
    ResPropMap[V] = RP;
    for (User *U : V->users()) {
      if (isa<GEPOperator>(U)) {
        PropagateResMap(U, Res);
      } else if (CallInst *CI = dyn_cast<CallInst>(U)) {
        // Stop propagate on function call.
        DxilInst_CreateHandleForLib Hdl(CI);
        if (Hdl) {
          DxilResourceProperties RP =
              resource_helper::loadPropsFromResourceBase(Res);
          ResPropMap[CI] = RP;
        }
      } else if (isa<LoadInst>(U)) {
        PropagateResMap(U, Res);
      } else if (isa<BitCastOperator>(U) && U->user_empty()) {
        // For hlsl type.
        continue;
      } else {
        EmitResourceError(Res, ValidationRule::InstrResourceUser);
      }
    }
  }
}

void ValidationContext::BuildResMap() {
  hlsl::OP *hlslOP = DxilMod.GetOP();

  if (IsLibProfile) {
    std::unordered_set<Value *> ResSet;
    // Start from all global variable in resTab.
    for (auto &Res : DxilMod.GetCBuffers())
      PropagateResMap(Res->GetGlobalSymbol(), Res.get());
    for (auto &Res : DxilMod.GetUAVs())
      PropagateResMap(Res->GetGlobalSymbol(), Res.get());
    for (auto &Res : DxilMod.GetSRVs())
      PropagateResMap(Res->GetGlobalSymbol(), Res.get());
    for (auto &Res : DxilMod.GetSamplers())
      PropagateResMap(Res->GetGlobalSymbol(), Res.get());
  } else {
    // Scan all createHandle.
    for (auto &It : hlslOP->GetOpFuncList(DXIL::OpCode::CreateHandle)) {
      Function *F = It.second;
      if (!F)
        continue;
      for (User *U : F->users()) {
        CallInst *CI = cast<CallInst>(U);
        DxilInst_CreateHandle Hdl(CI);
        // Validate Class/RangeID/Index.
        Value *ResClass = Hdl.get_resourceClass();
        if (!isa<ConstantInt>(ResClass)) {
          EmitInstrError(CI, ValidationRule::InstrOpConstRange);
          continue;
        }
        Value *RangeIndex = Hdl.get_rangeId();
        if (!isa<ConstantInt>(RangeIndex)) {
          EmitInstrError(CI, ValidationRule::InstrOpConstRange);
          continue;
        }

        DxilResourceBase *Res = nullptr;
        unsigned RangeId = Hdl.get_rangeId_val();
        switch (static_cast<DXIL::ResourceClass>(Hdl.get_resourceClass_val())) {
        default:
          EmitInstrError(CI, ValidationRule::InstrOpConstRange);
          continue;
          break;
        case DXIL::ResourceClass::CBuffer:
          if (DxilMod.GetCBuffers().size() > RangeId) {
            Res = &DxilMod.GetCBuffer(RangeId);
          } else {
            // Emit Error.
            EmitInstrError(CI, ValidationRule::InstrOpConstRange);
            continue;
          }
          break;
        case DXIL::ResourceClass::Sampler:
          if (DxilMod.GetSamplers().size() > RangeId) {
            Res = &DxilMod.GetSampler(RangeId);
          } else {
            // Emit Error.
            EmitInstrError(CI, ValidationRule::InstrOpConstRange);
            continue;
          }
          break;
        case DXIL::ResourceClass::SRV:
          if (DxilMod.GetSRVs().size() > RangeId) {
            Res = &DxilMod.GetSRV(RangeId);
          } else {
            // Emit Error.
            EmitInstrError(CI, ValidationRule::InstrOpConstRange);
            continue;
          }
          break;
        case DXIL::ResourceClass::UAV:
          if (DxilMod.GetUAVs().size() > RangeId) {
            Res = &DxilMod.GetUAV(RangeId);
          } else {
            // Emit Error.
            EmitInstrError(CI, ValidationRule::InstrOpConstRange);
            continue;
          }
          break;
        }

        ConstantInt *CIndex = dyn_cast<ConstantInt>(Hdl.get_index());
        if (!Res->GetHLSLType()->getPointerElementType()->isArrayTy()) {
          if (!CIndex) {
            // index must be 0 for none array resource.
            EmitInstrError(CI, ValidationRule::InstrOpConstRange);
            continue;
          }
        }
        if (CIndex) {
          unsigned Index = CIndex->getLimitedValue();
          if (Index < Res->GetLowerBound() || Index > Res->GetUpperBound()) {
            // index out of range.
            EmitInstrError(CI, ValidationRule::InstrOpConstRange);
            continue;
          }
        }
        HandleResIndexMap[CI] = RangeId;
        DxilResourceProperties RP =
            resource_helper::loadPropsFromResourceBase(Res);
        ResPropMap[CI] = RP;
      }
    }
  }
  const ShaderModel &SM = *DxilMod.GetShaderModel();

  for (auto &It : hlslOP->GetOpFuncList(DXIL::OpCode::AnnotateHandle)) {
    Function *F = It.second;
    if (!F)
      continue;

    for (User *U : F->users()) {
      CallInst *CI = cast<CallInst>(U);
      DxilInst_AnnotateHandle Hdl(CI);
      DxilResourceProperties RP =
          resource_helper::loadPropsFromAnnotateHandle(Hdl, SM);
      if (RP.getResourceKind() == DXIL::ResourceKind::Invalid) {
        EmitInstrError(CI, ValidationRule::InstrOpConstRange);
        continue;
      }

      ResPropMap[CI] = RP;
    }
  }
}

bool ValidationContext::HasEntryStatus(Function *F) {
  return EntryStatusMap.find(F) != EntryStatusMap.end();
}

EntryStatus &ValidationContext::GetEntryStatus(Function *F) {
  return *EntryStatusMap[F];
}

CallGraph &ValidationContext::GetCallGraph() {
  if (!CG)
    CG = llvm::make_unique<CallGraph>(M);
  return *CG.get();
}

void ValidationContext::EmitGlobalVariableFormatError(
    GlobalVariable *GV, ValidationRule Rule, ArrayRef<StringRef> Args) {
  std::string RuleText = GetValidationRuleText(Rule);
  FormatRuleText(RuleText, Args);
  if (DebugModule)
    GV = DebugModule->getGlobalVariable(GV->getName());
  dxilutil::EmitErrorOnGlobalVariable(M.getContext(), GV, RuleText);
  Failed = true;
}

// This is the least desirable mechanism, as it has no context.
void ValidationContext::EmitError(ValidationRule Rule) {
  dxilutil::EmitErrorOnContext(M.getContext(), GetValidationRuleText(Rule));
  Failed = true;
}

void ValidationContext::FormatRuleText(std::string &RuleText,
                                       ArrayRef<StringRef> Args) {
  std::string EscapedArg;
  // Consider changing const char * to StringRef
  for (unsigned I = 0; I < Args.size(); I++) {
    std::string ArgIdx = "%" + std::to_string(I);
    StringRef Arg = Args[I];
    if (Arg == "")
      Arg = "<null>";
    if (Arg[0] == 1) {
      EscapedArg = "";
      raw_string_ostream OS(EscapedArg);
      dxilutil::PrintEscapedString(Arg, OS);
      OS.flush();
      Arg = EscapedArg;
    }

    std::string::size_type Offset = RuleText.find(ArgIdx);
    if (Offset == std::string::npos)
      continue;

    unsigned Size = ArgIdx.size();
    RuleText.replace(Offset, Size, Arg);
  }
}

void ValidationContext::EmitFormatError(ValidationRule Rule,
                                        ArrayRef<StringRef> Args) {
  std::string RuleText = GetValidationRuleText(Rule);
  FormatRuleText(RuleText, Args);
  dxilutil::EmitErrorOnContext(M.getContext(), RuleText);
  Failed = true;
}

void ValidationContext::EmitMetaError(Metadata *Meta, ValidationRule Rule) {
  std::string O;
  raw_string_ostream OSS(O);
  Meta->print(OSS, &M);
  dxilutil::EmitErrorOnContext(M.getContext(), GetValidationRuleText(Rule) + O);
  Failed = true;
}

// Use this instead of DxilResourceBase::GetGlobalName
std::string
ValidationContext::GetResourceName(const hlsl::DxilResourceBase *Res) {
  if (!Res)
    return "nullptr";
  std::string ResName = Res->GetGlobalName();
  if (!ResName.empty())
    return ResName;
  if (DebugModule) {
    DxilModule &DM = DebugModule->GetOrCreateDxilModule();
    switch (Res->GetClass()) {
    case DXIL::ResourceClass::CBuffer:
      return DM.GetCBuffer(Res->GetID()).GetGlobalName();
    case DXIL::ResourceClass::Sampler:
      return DM.GetSampler(Res->GetID()).GetGlobalName();
    case DXIL::ResourceClass::SRV:
      return DM.GetSRV(Res->GetID()).GetGlobalName();
    case DXIL::ResourceClass::UAV:
      return DM.GetUAV(Res->GetID()).GetGlobalName();
    default:
      return "Invalid Resource";
    }
  }
  // When names have been stripped, use class and binding location to
  // identify the resource.  Format is roughly:
  // Allocated:   (CB|T|U|S)<ID>: <ResourceKind> ((cb|t|u|s)<LB>[<RangeSize>]
  // space<SpaceID>) Unallocated: (CB|T|U|S)<ID>: <ResourceKind> (no bind
  // location) Example: U0: TypedBuffer (u5[2] space1)
  // [<RangeSize>] and space<SpaceID> skipped if 1 and 0 respectively.
  return (Twine(Res->GetResIDPrefix()) + Twine(Res->GetID()) + ": " +
          Twine(Res->GetResKindName()) +
          (Res->IsAllocated() ? (" (" + Twine(Res->GetResBindPrefix()) +
                                 Twine(Res->GetLowerBound()) +
                                 (Res->IsUnbounded() ? Twine("[unbounded]")
                                  : (Res->GetRangeSize() != 1)
                                      ? "[" + Twine(Res->GetRangeSize()) + "]"
                                      : Twine()) +
                                 ((Res->GetSpaceID() != 0)
                                      ? " space" + Twine(Res->GetSpaceID())
                                      : Twine()) +
                                 ")")
                              : Twine(" (no bind location)")))
      .str();
}

void ValidationContext::EmitResourceError(const hlsl::DxilResourceBase *Res,
                                          ValidationRule Rule) {
  std::string QuotedRes = " '" + GetResourceName(Res) + "'";
  dxilutil::EmitErrorOnContext(M.getContext(),
                               GetValidationRuleText(Rule) + QuotedRes);
  Failed = true;
}

void ValidationContext::EmitResourceFormatError(
    const hlsl::DxilResourceBase *Res, ValidationRule Rule,
    ArrayRef<StringRef> Args) {
  std::string QuotedRes = " '" + GetResourceName(Res) + "'";
  std::string RuleText = GetValidationRuleText(Rule);
  FormatRuleText(RuleText, Args);
  dxilutil::EmitErrorOnContext(M.getContext(), RuleText + QuotedRes);
  Failed = true;
}

bool ValidationContext::IsDebugFunctionCall(Instruction *I) {
  return isa<DbgInfoIntrinsic>(I);
}

Instruction *ValidationContext::GetDebugInstr(Instruction *I) {
  DXASSERT_NOMSG(I);
  if (DebugModule) {
    // Look up the matching instruction in the debug module.
    llvm::Function *Fn = I->getParent()->getParent();
    llvm::Function *DbgFn = DebugModule->getFunction(Fn->getName());
    if (DbgFn) {
      // Linear lookup, but then again, failing validation is rare.
      inst_iterator It = inst_begin(Fn);
      inst_iterator DbgIt = inst_begin(DbgFn);
      while (IsDebugFunctionCall(&*DbgIt))
        ++DbgIt;
      while (&*It != I) {
        ++It;
        ++DbgIt;
        while (IsDebugFunctionCall(&*DbgIt))
          ++DbgIt;
      }
      return &*DbgIt;
    }
  }
  return I;
}

// Emit Error or note on instruction `I` with `Msg`.
// If `IsError` is true, `Rule` may omit repeated errors
void ValidationContext::EmitInstrDiagMsg(Instruction *I, ValidationRule Rule,
                                         std::string Msg, bool IsError) {
  BasicBlock *BB = I->getParent();
  Function *F = BB->getParent();

  Instruction *DbgI = GetDebugInstr(I);
  if (IsError) {
    if (const DebugLoc L = DbgI->getDebugLoc()) {
      // Instructions that get scalarized will likely hit
      // this case. Avoid redundant diagnostic messages.
      if (Rule == LastRuleEmit && L == LastDebugLocEmit) {
        return;
      }
      LastRuleEmit = Rule;
      LastDebugLocEmit = L;
    }
    dxilutil::EmitErrorOnInstruction(DbgI, Msg);
  } else {
    dxilutil::EmitNoteOnContext(DbgI->getContext(), Msg);
  }

  // Add llvm information as a note to instruction string
  std::string InstrStr;
  raw_string_ostream InstrStream(InstrStr);
  I->print(InstrStream, SlotTracker);
  InstrStream.flush();
  StringRef InstrStrRef = InstrStr;
  InstrStrRef = InstrStrRef.ltrim(); // Ignore indentation
  Msg = "at '" + InstrStrRef.str() + "'";

  // Print the parent block name
  Msg += " in block '";
  if (!BB->getName().empty()) {
    Msg += BB->getName();
  } else {
    unsigned Idx = 0;
    for (auto BI = F->getBasicBlockList().begin(),
              BE = F->getBasicBlockList().end();
         BI != BE; ++BI) {
      if (BB == &(*BI)) {
        break;
      }
      Idx++;
    }
    Msg += "#" + std::to_string(Idx);
  }
  Msg += "'";

  // Print the function name
  Msg += " of function '" + F->getName().str() + "'.";

  dxilutil::EmitNoteOnContext(DbgI->getContext(), Msg);

  Failed = true;
}

void ValidationContext::EmitInstrError(Instruction *I, ValidationRule Rule) {
  EmitInstrDiagMsg(I, Rule, GetValidationRuleText(Rule));
}

void ValidationContext::EmitInstrNote(Instruction *I, std::string Msg) {
  EmitInstrDiagMsg(I, LastRuleEmit, Msg, false);
}

void ValidationContext::EmitInstrFormatError(Instruction *I,
                                             ValidationRule Rule,
                                             ArrayRef<StringRef> Args) {
  std::string RuleText = GetValidationRuleText(Rule);
  FormatRuleText(RuleText, Args);
  EmitInstrDiagMsg(I, Rule, RuleText);
}

void ValidationContext::EmitSignatureError(DxilSignatureElement *SE,
                                           ValidationRule Rule) {
  EmitFormatError(Rule, {SE->GetName()});
}

void ValidationContext::EmitTypeError(Type *Ty, ValidationRule Rule) {
  std::string O;
  raw_string_ostream OSS(O);
  Ty->print(OSS);
  EmitFormatError(Rule, {OSS.str()});
}

void ValidationContext::EmitFnError(Function *F, ValidationRule Rule) {
  if (DebugModule)
    if (Function *DbgF = DebugModule->getFunction(F->getName()))
      F = DbgF;
  dxilutil::EmitErrorOnFunction(M.getContext(), F, GetValidationRuleText(Rule));
  Failed = true;
}

void ValidationContext::EmitFnFormatError(Function *F, ValidationRule Rule,
                                          ArrayRef<StringRef> Args) {
  std::string RuleText = GetValidationRuleText(Rule);
  FormatRuleText(RuleText, Args);
  if (DebugModule)
    if (Function *DbgF = DebugModule->getFunction(F->getName()))
      F = DbgF;
  dxilutil::EmitErrorOnFunction(M.getContext(), F, RuleText);
  Failed = true;
}

void ValidationContext::EmitFnAttributeError(Function *F, StringRef Kind,
                                             StringRef Value) {
  EmitFnFormatError(F, ValidationRule::DeclFnAttribute,
                    {F->getName(), Kind, Value});
}

} // namespace hlsl
