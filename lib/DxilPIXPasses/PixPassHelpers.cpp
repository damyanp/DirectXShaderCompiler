///////////////////////////////////////////////////////////////////////////////
//                                                                           //
// PixPassHelpers.cpp
// // Copyright (C) Microsoft Corporation. All rights reserved. // This file is
// distributed under the University of Illinois Open Source     // License. See
// LICENSE.TXT for details.                                     //
//                                                                           //
///////////////////////////////////////////////////////////////////////////////

#include "dxc/DXIL/DxilFunctionProps.h"
#include "dxc/DXIL/DxilInstructions.h"
#include "dxc/DXIL/DxilModule.h"
#include "dxc/DXIL/DxilOperations.h"
#include "dxc/DXIL/DxilResourceBinding.h"
#include "dxc/DXIL/DxilResourceProperties.h"
#include "dxc/DxilRootSignature/DxilRootSignature.h"
#include "dxc/HLSL/DxilSpanAllocator.h"

#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Pass.h"

#include "PixPassHelpers.h"

#include "dxc/Support/Global.h"
#include "dxc/Support/WinIncludes.h"
#include "dxc/dxcapi.h"

#ifdef PIX_DEBUG_DUMP_HELPER
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include <iostream>
#endif

using namespace llvm;
using namespace hlsl;

namespace PIXPassHelpers {
static void FindRayQueryHandlesFromUse(Value *U,
                                       SmallPtrSetImpl<Value *> &Handles) {
  if (Handles.insert(U).second) {
    auto RayQueryHandleUses = U->uses();
    for (Use &Use : RayQueryHandleUses) {
      iterator_range<Value::user_iterator> Users = Use->users();
      for (User *User : Users) {
        if (isa<PHINode>(User) || isa<SelectInst>(User))
          FindRayQueryHandlesFromUse(User, Handles);
      }
    }
  }
}

void FindRayQueryHandlesForFunction(llvm::Function *F,
                                    SmallPtrSetImpl<Value *> &RayQueryHandles) {
  auto &blocks = F->getBasicBlockList();
  if (!blocks.empty()) {
    for (auto &block : blocks) {
      for (auto &instruction : block) {
        if (hlsl::OP::IsDxilOpFuncCallInst(
                &instruction, hlsl::OP::OpCode::AllocateRayQuery)) {
          FindRayQueryHandlesFromUse(&instruction, RayQueryHandles);
        }
      }
    }
  }
}

static bool IsDynamicResourceShaderModel(DxilModule &DM) {
  return DM.GetShaderModel()->IsSMAtLeast(6, 6);
}

static bool ShaderModelRequiresAnnotateHandle(DxilModule &DM) {
  return DM.GetShaderModel()->IsSMAtLeast(6, 6);
}

static char const *RawUAVType() { return "struct.RWByteAddressBuffer"; }
static char const *ShaderModelHandleTypeName(DxilModule &DM) {
  // Prior to sm6.6, lib handles were typed after the resource they denote.
  // In 6.6 and after, and in all non-lib shader models,
  // all handles are dx.types.Handle.
  if (!DM.GetShaderModel()->IsLib() || DM.GetShaderModel()->IsSM66Plus())
    return "dx.types.Handle";
  return RawUAVType();
}

llvm::CallInst *CreateHandleForResource(hlsl::DxilModule &DM,
                                        llvm::IRBuilder<> &Builder,
                                        hlsl::DxilResourceBase *resource,
                                        const char *name) {

  OP *HlslOP = DM.GetOP();
  LLVMContext &Ctx = DM.GetModule()->getContext();

  DXIL::ResourceClass resourceClass = resource->GetClass();

  auto const *shaderModel = DM.GetShaderModel();
  Type *resourceHandleType =
      DM.GetModule()->getTypeByName(ShaderModelHandleTypeName(DM));
  if (shaderModel->IsLib()) {
    llvm::Constant *object = resource->GetGlobalSymbol();
    Value *load = Builder.CreateLoad(object, resourceHandleType);
    llvm::cast<LoadInst>(load)->setAlignment(4);
    llvm::cast<LoadInst>(load)->setVolatile(false);
    Function *CreateHandleForLibOpFunc =
        HlslOP->GetOpFunc(DXIL::OpCode::CreateHandleForLib, load->getType());
    Constant *CreateHandleForLibOpcodeArg =
        HlslOP->GetU32Const((unsigned)DXIL::OpCode::CreateHandleForLib);
    auto *handle = Builder.CreateCall(CreateHandleForLibOpFunc,
                                      {CreateHandleForLibOpcodeArg, load});

    if (ShaderModelRequiresAnnotateHandle(DM)) {
      Function *annotHandleFn =
          HlslOP->GetOpFunc(DXIL::OpCode::AnnotateHandle, Type::getVoidTy(Ctx));
      Value *annotHandleArg =
          HlslOP->GetI32Const((unsigned)DXIL::OpCode::AnnotateHandle);
      DxilResourceProperties RP =
          resource_helper::loadPropsFromResourceBase(resource);
      Type *resPropertyTy = HlslOP->GetResourcePropertiesType();
      Value *propertiesV = resource_helper::getAsConstant(RP, resPropertyTy,
                                                          *DM.GetShaderModel());

      return Builder.CreateCall(annotHandleFn,
                                {annotHandleArg, handle, propertiesV});
    } else {
      return handle;
    }
  } else if (IsDynamicResourceShaderModel(DM)) {
    Function *CreateHandleFromBindingOpFunc = HlslOP->GetOpFunc(
        DXIL::OpCode::CreateHandleFromBinding, Type::getVoidTy(Ctx));
    Constant *CreateHandleFromBindingOpcodeArg =
        HlslOP->GetU32Const((unsigned)DXIL::OpCode::CreateHandleFromBinding);
    DxilResourceBinding binding =
        resource_helper::loadBindingFromResourceBase(resource);
    Value *bindingV = resource_helper::getAsConstant(
        binding, HlslOP->GetResourceBindingType(), *DM.GetShaderModel());

    Value *registerIndex = HlslOP->GetU32Const(0);

    Value *isUniformRes = HlslOP->GetI1Const(0);

    Value *createHandleFromBindingArgs[] = {CreateHandleFromBindingOpcodeArg,
                                            bindingV, registerIndex,
                                            isUniformRes};

    auto *handle = Builder.CreateCall(CreateHandleFromBindingOpFunc,
                                      createHandleFromBindingArgs, name);

    Function *annotHandleFn =
        HlslOP->GetOpFunc(DXIL::OpCode::AnnotateHandle, Type::getVoidTy(Ctx));
    Value *annotHandleArg =
        HlslOP->GetI32Const((unsigned)DXIL::OpCode::AnnotateHandle);
    DxilResourceProperties RP =
        resource_helper::loadPropsFromResourceBase(resource);
    Type *resPropertyTy = HlslOP->GetResourcePropertiesType();
    Value *propertiesV =
        resource_helper::getAsConstant(RP, resPropertyTy, *DM.GetShaderModel());

    return Builder.CreateCall(annotHandleFn,
                              {annotHandleArg, handle, propertiesV});
  } else {
    Function *CreateHandleOpFunc =
        HlslOP->GetOpFunc(DXIL::OpCode::CreateHandle, Type::getVoidTy(Ctx));
    Constant *CreateHandleOpcodeArg =
        HlslOP->GetU32Const((unsigned)DXIL::OpCode::CreateHandle);
    Constant *ClassArg = HlslOP->GetI8Const(
        static_cast<std::underlying_type<DxilResourceBase::Class>::type>(
            resourceClass));
    Constant *MetaDataArg = HlslOP->GetU32Const(resource->GetID());
    Constant *IndexArg = HlslOP->GetU32Const(0);
    Constant *FalseArg =
        HlslOP->GetI1Const(0); // non-uniform resource index: false
    return Builder.CreateCall(
        CreateHandleOpFunc,
        {CreateHandleOpcodeArg, ClassArg, MetaDataArg, IndexArg, FalseArg},
        name);
  }
}

static std::vector<uint8_t> SerializeRootSignatureToVector(
    DxilVersionedRootSignatureDesc const *rootSignature) {
  CComPtr<IDxcBlob> serializedRootSignature;
  CComPtr<IDxcBlobEncoding> errorBlob;
  constexpr bool allowReservedRegisterSpace = true;
  SerializeRootSignature(rootSignature, &serializedRootSignature, &errorBlob,
                         allowReservedRegisterSpace);
  std::vector<uint8_t> ret;
  if (serializedRootSignature == nullptr) {
    return ret;
  }
  auto const *serializedData = reinterpret_cast<const uint8_t *>(
      serializedRootSignature->GetBufferPointer());
  ret.assign(serializedData,
             serializedData + serializedRootSignature->GetBufferSize());

  return ret;
}

constexpr uint32_t toolsRegisterSpace = static_cast<uint32_t>(-2);

// Returns whether a parameter was appended.
template <typename RootSigDesc, typename RootParameterDesc>
bool ExtendRootSig(RootSigDesc &rootSigDesc, uint32_t toolsUAVRegister) {
  auto *existingParams = rootSigDesc.pParameters;
  for (uint32_t i = 0; i < rootSigDesc.NumParameters; ++i) {
    if (rootSigDesc.pParameters[i].ParameterType ==
        DxilRootParameterType::UAV) {
      if (rootSigDesc.pParameters[i].Descriptor.RegisterSpace ==
              toolsRegisterSpace &&
          rootSigDesc.pParameters[i].Descriptor.ShaderRegister ==
              toolsUAVRegister) {
        // Already added
        return false;
      }
    }
  }
  auto *newParams = new RootParameterDesc[rootSigDesc.NumParameters + 1];
  if (existingParams != nullptr) {
    memcpy(newParams, existingParams,
           rootSigDesc.NumParameters * sizeof(RootParameterDesc));
    delete[] existingParams;
  }
  rootSigDesc.pParameters = newParams;
  rootSigDesc.pParameters[rootSigDesc.NumParameters].ParameterType =
      DxilRootParameterType::UAV;
  rootSigDesc.pParameters[rootSigDesc.NumParameters].Descriptor.RegisterSpace =
      toolsRegisterSpace;
  rootSigDesc.pParameters[rootSigDesc.NumParameters].Descriptor.ShaderRegister =
      toolsUAVRegister;
  rootSigDesc.pParameters[rootSigDesc.NumParameters].ShaderVisibility =
      DxilShaderVisibility::All;
  rootSigDesc.NumParameters++;
  return true;
}

static std::vector<uint8_t>
AddUAVParamterToRootSignature(const void *Data, uint32_t Size,
                              uint32_t toolsUAVRegister) {
  DxilVersionedRootSignature rootSignature;
  DeserializeRootSignature(Data, Size, rootSignature.get_address_of());
  auto *rs = rootSignature.get_mutable();
  switch (rootSignature->Version) {
  case DxilRootSignatureVersion::Version_1_0:
    ExtendRootSig<DxilRootSignatureDesc, DxilRootParameter>(rs->Desc_1_0,
                                                            toolsUAVRegister);
    break;
  case DxilRootSignatureVersion::Version_1_1:
    if (ExtendRootSig<DxilRootSignatureDesc1, DxilRootParameter1>(
            rs->Desc_1_1, toolsUAVRegister)) {
      rs->Desc_1_1.pParameters[rs->Desc_1_1.NumParameters - 1]
          .Descriptor.Flags = hlsl::DxilRootDescriptorFlags::None;
    }
    break;
  }
  return SerializeRootSignatureToVector(rs);
}

static void AddUAVToShaderAttributeRootSignature(DxilModule &DM,
                                                 uint32_t toolsUAVRegister) {
  auto rs = DM.GetSerializedRootSignature();
  if (!rs.empty()) {
    std::vector<uint8_t> asVector = AddUAVParamterToRootSignature(
        rs.data(), static_cast<uint32_t>(rs.size()), toolsUAVRegister);
    if (!asVector.empty()) {
      DM.ResetSerializedRootSignature(asVector);
    }
  }
}

static void AddUAVToDxilDefinedGlobalRootSignatures(DxilModule &DM,
                                                    uint32_t toolsUAVRegister) {
  struct ReplacementRootSignature {
    std::string Name;
    std::vector<uint8_t> Data;
  };

  std::vector<ReplacementRootSignature> replacementRootSignatures;
  auto *subObjects = DM.GetSubobjects();
  if (subObjects != nullptr) {
    for (auto const &subObject : subObjects->GetSubobjects()) {
      if (subObject.second->GetKind() ==
          DXIL::SubobjectKind::GlobalRootSignature) {
        const void *Data = nullptr;
        uint32_t Size = 0;
        constexpr bool notALocalRS = false;
        if (subObject.second->GetRootSignature(notALocalRS, Data, Size,
                                               nullptr)) {
          std::vector<uint8_t> extended =
              AddUAVParamterToRootSignature(Data, Size, toolsUAVRegister);
          if (!extended.empty()) {
            replacementRootSignatures.push_back(
                {subObject.first.str(), std::move(extended)});
          }
        }
      }
    }

    constexpr bool notALocalRS = false;
    for (auto const &replacementRootSignature : replacementRootSignatures) {
      subObjects->RemoveSubobject(replacementRootSignature.Name);
      subObjects->CreateRootSignature(
          replacementRootSignature.Name, notALocalRS,
          replacementRootSignature.Data.data(),
          static_cast<uint32_t>(replacementRootSignature.Data.size()));
    }
  }
}

// Set up a UAV with structure of a single int. The caller must have
// already confirmed hlslBindIndex has no existing resource.
static hlsl::DxilResource *
CreateNewGlobalUAVResource(hlsl::DxilModule &DM, unsigned int hlslBindIndex,
                           const char *name) {
  LLVMContext &Ctx = DM.GetModule()->getContext();

  const char *PIXStructTypeName = ShaderModelHandleTypeName(DM);
  llvm::StructType *UAVStructTy =
      DM.GetModule()->getTypeByName(PIXStructTypeName);

  if (UAVStructTy == nullptr) {
    SmallVector<llvm::Type *, 1> Elements{Type::getInt32Ty(Ctx)};
    UAVStructTy = llvm::StructType::create(Elements, PIXStructTypeName);
  }

  unsigned int Id = static_cast<unsigned int>(DM.GetUAVs().size());
  std::unique_ptr<DxilResource> pUAV = llvm::make_unique<DxilResource>();
  pUAV->SetID(Id);

  auto const *shaderModel = DM.GetShaderModel();
  std::string PixUavName = "PIXUAV" + std::to_string(hlslBindIndex);
  if (shaderModel->IsLib()) {
    auto *Global =
        DM.GetModule()->getOrInsertGlobal(PixUavName.c_str(), UAVStructTy);
    GlobalVariable *NewGV = cast<GlobalVariable>(Global);
    NewGV->setConstant(true);
    NewGV->setLinkage(GlobalValue::ExternalLinkage);
    NewGV->setThreadLocal(false);
    NewGV->setAlignment(4);
    pUAV->SetGlobalSymbol(NewGV);
  } else {
    pUAV->SetGlobalSymbol(UndefValue::get(UAVStructTy->getPointerTo()));
  }
  pUAV->SetGlobalName(name);
  pUAV->SetRW(true);                    // sets UAV class
  pUAV->SetSpaceID(toolsRegisterSpace); // reserved-for-tools register space
  pUAV->SetSampleCount(0); // This is what compiler generates for a raw UAV
  pUAV->SetGloballyCoherent(false);
  pUAV->SetReorderCoherent(false);
  pUAV->SetHasCounter(false);
  pUAV->SetCompType(
      CompType::getInvalid()); // This is what compiler generates for a raw UAV
  pUAV->SetLowerBound(hlslBindIndex);
  pUAV->SetRangeSize(1);
  pUAV->SetElementStride(1);
  pUAV->SetKind(DXIL::ResourceKind::RawBuffer);
  auto HLSLType = DM.GetModule()->getTypeByName(RawUAVType());
  if (HLSLType == nullptr) {
    SmallVector<llvm::Type *, 1> Elements{Type::getInt32Ty(Ctx)};
    HLSLType = llvm::StructType::create(Elements, RawUAVType());
  }
  pUAV->SetHLSLType(HLSLType->getPointerTo());

  auto pAnnotation = DM.GetTypeSystem().GetStructAnnotation(UAVStructTy);
  if (pAnnotation == nullptr) {

    pAnnotation = DM.GetTypeSystem().AddStructAnnotation(UAVStructTy);
    pAnnotation->GetFieldAnnotation(0).SetCBufferOffset(0);
    pAnnotation->GetFieldAnnotation(0).SetCompType(
        hlsl::DXIL::ComponentType::I32);
    pAnnotation->GetFieldAnnotation(0).SetFieldName("count");
  }

  auto *ret = pUAV.get();
  DM.AddUAV(std::move(pUAV));
  DM.CollectShaderFlagsForModule();
  return ret;
}

// Set up a UAV with structure of a single int
hlsl::DxilResource *CreateGlobalUAVResource(hlsl::DxilModule &DM,
                                            unsigned int hlslBindIndex,
                                            const char *name) {
  for (auto const &existingUAV : DM.GetUAVs()) {
    if (existingUAV->GetSpaceID() == toolsRegisterSpace &&
        existingUAV->GetLowerBound() == hlslBindIndex) {
      return existingUAV.get();
    }
  }

  AddUAVToDxilDefinedGlobalRootSignatures(DM, hlslBindIndex);
  AddUAVToShaderAttributeRootSignature(DM, hlslBindIndex);

  return CreateNewGlobalUAVResource(DM, hlslBindIndex, name);
}

void EraseIfUnused(hlsl::DxilModule &DM, llvm::Function *OpFunction) {
  if (OpFunction != nullptr && OpFunction->user_empty()) {
    DM.GetOP()->RemoveFunction(OpFunction);
    OpFunction->eraseFromParent();
  }
}

// Set up a UAV with structure of a single int
llvm::CallInst *CreateUAVOnceForModule(hlsl::DxilModule &DM,
                                       llvm::IRBuilder<> &Builder,
                                       unsigned int hlslBindIndex,
                                       const char *name) {
  auto uav = CreateGlobalUAVResource(DM, hlslBindIndex, name);
  auto *handle = CreateHandleForResource(DM, Builder, uav, name);

  return handle;
}

// The D3D12 root-signature cost budget, in 32-bit DWORDs: a descriptor
// table costs 1, a root constant costs one DWORD per 32-bit value, and a
// root descriptor (CBV/SRV/UAV) costs 2.
constexpr uint32_t kMaxRootSignatureCostInDwords = 64;

template <typename RootSigDesc>
static uint32_t RootSignatureCostInDwords(const RootSigDesc &rootSigDesc) {
  uint32_t cost = 0;
  for (uint32_t i = 0; i < rootSigDesc.NumParameters; ++i) {
    switch (rootSigDesc.pParameters[i].ParameterType) {
    case DxilRootParameterType::DescriptorTable:
      cost += 1;
      break;
    case DxilRootParameterType::Constants32Bit:
      cost += rootSigDesc.pParameters[i].Constants.Num32BitValues;
      break;
    default: // CBV, SRV, UAV: one root descriptor each.
      cost += 2;
      break;
    }
  }
  return cost;
}

// v1.0 root descriptors have no per-descriptor Flags; nothing to clear.
static void ClearNewUAVFlags(DxilRootParameter *, uint32_t, uint32_t) {}
// v1.1 root descriptors do; clear Flags only on the newly appended range
// [firstNewIndex, newCount), never on a pre-existing parameter.
static void ClearNewUAVFlags(DxilRootParameter1 *params, uint32_t firstNewIndex,
                             uint32_t newCount) {
  for (uint32_t i = firstNewIndex; i < newCount; ++i) {
    params[i].Descriptor.Flags = hlsl::DxilRootDescriptorFlags::None;
  }
}

// Extends rootSigDesc to include every register in registersToAdd not
// already present as a tools UAV, honoring the D3D12 64-DWORD budget, as
// one atomic operation: either every register is added and the result
// fits, or rootSigDesc is left completely unmodified and this returns
// false. *outChanged reports whether anything was actually added (every
// requested register may already have been present).
template <typename RootSigDesc, typename RootParameterDesc>
static bool ExtendRootSigBatch(RootSigDesc &rootSigDesc,
                               llvm::ArrayRef<uint32_t> registersToAdd,
                               bool *outChanged) {
  *outChanged = false;
  std::vector<uint32_t> newRegisters;
  for (uint32_t reg : registersToAdd) {
    bool present = false;
    for (uint32_t i = 0; i < rootSigDesc.NumParameters; ++i) {
      if (rootSigDesc.pParameters[i].ParameterType ==
              DxilRootParameterType::UAV &&
          rootSigDesc.pParameters[i].Descriptor.RegisterSpace ==
              toolsRegisterSpace &&
          rootSigDesc.pParameters[i].Descriptor.ShaderRegister == reg) {
        present = true;
        break;
      }
    }
    if (!present) {
      newRegisters.push_back(reg);
    }
  }
  if (newRegisters.empty()) {
    return true; // Nothing to add: idempotent success.
  }

  const uint32_t firstNewIndex = rootSigDesc.NumParameters;
  const uint32_t newCount =
      firstNewIndex + static_cast<uint32_t>(newRegisters.size());

  // Stage the extended array; rootSigDesc is not touched until the whole
  // staged result is confirmed within budget.
  std::unique_ptr<RootParameterDesc[]> staged(new RootParameterDesc[newCount]);
  if (rootSigDesc.pParameters != nullptr) {
    memcpy(staged.get(), rootSigDesc.pParameters,
           firstNewIndex * sizeof(RootParameterDesc));
  }
  uint32_t writeIndex = firstNewIndex;
  for (uint32_t reg : newRegisters) {
    staged[writeIndex].ParameterType = DxilRootParameterType::UAV;
    staged[writeIndex].Descriptor.RegisterSpace = toolsRegisterSpace;
    staged[writeIndex].Descriptor.ShaderRegister = reg;
    staged[writeIndex].ShaderVisibility = DxilShaderVisibility::All;
    ++writeIndex;
  }

  RootSigDesc stagedDesc = rootSigDesc;
  stagedDesc.pParameters = staged.get();
  stagedDesc.NumParameters = newCount;
  if (RootSignatureCostInDwords(stagedDesc) > kMaxRootSignatureCostInDwords) {
    return false; // Over budget: rootSigDesc untouched.
  }

  ClearNewUAVFlags(staged.get(), firstNewIndex, newCount);
  RootParameterDesc *oldParams = rootSigDesc.pParameters;
  rootSigDesc.pParameters = staged.release();
  rootSigDesc.NumParameters = newCount;
  delete[] oldParams;
  *outChanged = true;
  return true;
}

// The outcome of planning one root signature's batch extension. Fits is
// false when adding registersToAdd would exceed the budget or the
// extended signature fails the serializer's own validation (e.g. a
// duplicate register binding); the signature is then left out of the
// commit in ExtendAllGlobalRootSignaturesAtomically.
struct RootSignatureUpdatePlan {
  bool Fits = false;
  bool Changed = false;
  std::vector<uint8_t> Bytes;
};

static RootSignatureUpdatePlan
PlanRootSignatureUpdate(const void *Data, uint32_t Size,
                        llvm::ArrayRef<uint32_t> registersToAdd) {
  RootSignatureUpdatePlan plan;
  DxilVersionedRootSignature rootSignature;
  DeserializeRootSignature(Data, Size, rootSignature.get_address_of());
  DxilVersionedRootSignatureDesc *rs = rootSignature.get_mutable();
  bool changed = false;
  switch (rootSignature->Version) {
  case DxilRootSignatureVersion::Version_1_0:
    plan.Fits = ExtendRootSigBatch<DxilRootSignatureDesc, DxilRootParameter>(
        rs->Desc_1_0, registersToAdd, &changed);
    break;
  case DxilRootSignatureVersion::Version_1_1:
    plan.Fits = ExtendRootSigBatch<DxilRootSignatureDesc1, DxilRootParameter1>(
        rs->Desc_1_1, registersToAdd, &changed);
    break;
  }
  if (!plan.Fits) {
    return plan;
  }
  plan.Changed = changed;
  if (changed) {
    plan.Bytes = SerializeRootSignatureToVector(rs);
    if (plan.Bytes.empty()) {
      plan.Fits = false;
      plan.Changed = false;
    }
  }
  return plan;
}

// Applies registersToAdd to every global root signature associated with
// DM -- the shader-attribute root signature and every DXIL-defined
// global root signature subobject -- as one atomic transaction: either
// every one of them fits the D3D12 64-DWORD budget and all are updated,
// or none of them are.
static bool ExtendAllGlobalRootSignaturesAtomically(
    DxilModule &DM, llvm::ArrayRef<uint32_t> registersToAdd) {
  struct SubobjectUpdate {
    std::string Name;
    std::vector<uint8_t> Bytes;
  };

  RootSignatureUpdatePlan shaderAttributePlan;
  const std::vector<uint8_t> &shaderAttributeRS =
      DM.GetSerializedRootSignature();
  if (!shaderAttributeRS.empty()) {
    shaderAttributePlan = PlanRootSignatureUpdate(
        shaderAttributeRS.data(),
        static_cast<uint32_t>(shaderAttributeRS.size()), registersToAdd);
    if (!shaderAttributePlan.Fits) {
      return false;
    }
  }

  std::vector<SubobjectUpdate> subobjectUpdates;
  DxilSubobjects *subObjects = DM.GetSubobjects();
  if (subObjects != nullptr) {
    for (const std::pair<llvm::StringRef, std::unique_ptr<DxilSubobject>>
             &subObject : subObjects->GetSubobjects()) {
      if (subObject.second->GetKind() !=
          DXIL::SubobjectKind::GlobalRootSignature) {
        continue;
      }
      const void *Data = nullptr;
      uint32_t Size = 0;
      constexpr bool notALocalRS = false;
      if (!subObject.second->GetRootSignature(notALocalRS, Data, Size,
                                              nullptr)) {
        continue;
      }
      RootSignatureUpdatePlan plan =
          PlanRootSignatureUpdate(Data, Size, registersToAdd);
      if (!plan.Fits) {
        return false;
      }
      if (plan.Changed) {
        subobjectUpdates.push_back(
            {subObject.first.str(), std::move(plan.Bytes)});
      }
    }
  }

  // Every target fits within budget: commit them all.
  if (shaderAttributePlan.Changed) {
    DM.ResetSerializedRootSignature(shaderAttributePlan.Bytes);
  }
  constexpr bool notALocalRS = false;
  for (SubobjectUpdate &update : subobjectUpdates) {
    subObjects->RemoveSubobject(update.Name);
    subObjects->CreateRootSignature(update.Name, notALocalRS,
                                    update.Bytes.data(),
                                    static_cast<uint32_t>(update.Bytes.size()));
  }
  return true;
}

// Creates a resource (if not already present) and access handle for
// every request, extending every root signature associated with DM to
// cover all newly-needed registers as one atomic transaction: if any one
// would exceed the D3D12 64-DWORD budget, Success is false and nothing
// -- no resource, root-signature change, or handle -- is created for any
// request. Callers must check Success before using Handles. requests
// must not repeat a register.
BatchUAVHandles CreateUAVHandlesOnceForModule(
    hlsl::DxilModule &DM, llvm::IRBuilder<> &Builder,
    llvm::ArrayRef<std::pair<unsigned int, const char *>> requests) {
  BatchUAVHandles result;

  std::vector<hlsl::DxilResource *> existing(requests.size(), nullptr);
  std::vector<uint32_t> registersToAdd;
  for (size_t i = 0; i < requests.size(); ++i) {
    for (const std::unique_ptr<DxilResource> &existingUAV : DM.GetUAVs()) {
      if (existingUAV->GetSpaceID() == toolsRegisterSpace &&
          existingUAV->GetLowerBound() == requests[i].first) {
        existing[i] = existingUAV.get();
        break;
      }
    }
    if (existing[i] == nullptr) {
      registersToAdd.push_back(requests[i].first);
    }
  }

  if (!registersToAdd.empty() &&
      !ExtendAllGlobalRootSignaturesAtomically(DM, registersToAdd)) {
    return result; // Success stays false: no mutation, no handles.
  }

  result.Handles.reserve(requests.size());
  for (size_t i = 0; i < requests.size(); ++i) {
    hlsl::DxilResource *uav =
        existing[i] != nullptr ? existing[i]
                               : CreateNewGlobalUAVResource(
                                     DM, requests[i].first, requests[i].second);
    result.Handles.push_back(
        CreateHandleForResource(DM, Builder, uav, requests[i].second));
  }
  result.Success = true;
  return result;
}

llvm::Function *GetEntryFunction(hlsl::DxilModule &DM) {
  if (DM.GetEntryFunction() != nullptr) {
    return DM.GetEntryFunction();
  }
  return DM.GetPatchConstantFunction();
}

std::vector<llvm::Function *>
GetAllInstrumentableFunctions(hlsl::DxilModule &DM) {

  std::vector<llvm::Function *> ret;

  for (llvm::Function &F : DM.GetModule()->functions()) {
    if (F.isDeclaration() || F.isIntrinsic() || hlsl::OP::IsDxilOpFunc(&F))
      continue;
    if (F.getBasicBlockList().empty())
      continue;
    ret.push_back(&F);
  }

  return ret;
}

hlsl::DXIL::ShaderKind GetFunctionShaderKind(hlsl::DxilModule &DM,
                                             llvm::Function *fn) {
  hlsl::DXIL::ShaderKind shaderKind = hlsl::DXIL::ShaderKind::Invalid;
  if (!DM.HasDxilFunctionProps(fn)) {
    auto ShaderModel = DM.GetShaderModel();
    shaderKind = ShaderModel->GetKind();
  } else {
    hlsl::DxilFunctionProps const &props = DM.GetDxilFunctionProps(fn);
    shaderKind = props.shaderKind;
  }
  return shaderKind;
}

ExpandedStruct ExpandStructType(LLVMContext &Ctx,
                                Type *OriginalPayloadStructType) {
  SmallVector<Type *, 16> Elements;
  for (unsigned int i = 0;
       i < OriginalPayloadStructType->getStructNumElements(); ++i) {
    Elements.push_back(OriginalPayloadStructType->getStructElementType(i));
  }
  Elements.push_back(Type::getInt32Ty(Ctx));
  Elements.push_back(Type::getInt32Ty(Ctx));
  Elements.push_back(Type::getInt32Ty(Ctx));
  ExpandedStruct ret;
  ret.ExpandedPayloadStructType =
      StructType::create(Ctx, Elements, "PIX_AS2MS_Expanded_Type");
  ret.ExpandedPayloadStructPtrType =
      ret.ExpandedPayloadStructType->getPointerTo();
  return ret;
}

void ReplaceAllUsesOfInstructionWithNewValueAndDeleteInstruction(
    Instruction *Instr, Value *newValue, Type *newType) {
  std::vector<Value *> users;
  for (auto u = Instr->user_begin(); u != Instr->user_end(); ++u) {
    users.push_back(*u);
  }

  for (auto user : users) {
    if (auto *instruction = llvm::cast<Instruction>(user)) {
      for (unsigned int i = 0; i < instruction->getNumOperands(); ++i) {
        auto *Operand = instruction->getOperand(i);
        if (Operand == Instr) {
          instruction->setOperand(i, newValue);
        }
      }
      if (llvm::isa<GetElementPtrInst>(instruction)) {
        auto *GEP = llvm::cast<GetElementPtrInst>(instruction);
        GEP->setSourceElementType(newType);
      } else if (hlsl::OP::IsDxilOpFuncCallInst(
                     instruction, hlsl::OP::OpCode::DispatchMesh)) {
        DxilModule &DM = instruction->getModule()->GetOrCreateDxilModule();
        OP *HlslOP = DM.GetOP();

        DxilInst_DispatchMesh DispatchMesh(instruction);
        IRBuilder<> B(instruction);
        SmallVector<Value *, 5> args;
        args.push_back(
            HlslOP->GetU32Const((unsigned)hlsl::OP::OpCode::DispatchMesh));
        args.push_back(DispatchMesh.get_threadGroupCountX());
        args.push_back(DispatchMesh.get_threadGroupCountY());
        args.push_back(DispatchMesh.get_threadGroupCountZ());
        args.push_back(newValue);

        B.CreateCall(HlslOP->GetOpFunc(DXIL::OpCode::DispatchMesh,
                                       newType->getPointerTo()),
                     args);

        instruction->removeFromParent();
        delete instruction;
      }
    }
  }

  Instr->removeFromParent();
  delete Instr;
}

unsigned int FindOrAddSV_Position(hlsl::DxilModule &DM,
                                  unsigned UpStreamSVPosRow) {
  hlsl::DxilSignature &InputSignature = DM.GetInputSignature();
  auto &InputElements = InputSignature.GetElements();

  auto Existing_SV_Position =
      std::find_if(InputElements.begin(), InputElements.end(),
                   [](const std::unique_ptr<DxilSignatureElement> &Element) {
                     return Element->GetSemantic()->GetKind() ==
                            hlsl::DXIL::SemanticKind::Position;
                   });

  // SV_Position, if present, has to have full mask, so we needn't worry
  // about the shader having selected components that don't include x or y.
  // If not present, we add it.
  if (Existing_SV_Position == InputElements.end()) {
    unsigned int StartColumn = 0;
    unsigned int RowCount = 1;
    unsigned int ColumnCount = 4;
    auto Added_SV_Position =
        llvm::make_unique<DxilSignatureElement>(DXIL::SigPointKind::PSIn);
    Added_SV_Position->Initialize("Position", hlsl::CompType::getF32(),
                                  hlsl::DXIL::InterpolationMode::Linear,
                                  RowCount, ColumnCount, UpStreamSVPosRow,
                                  StartColumn);
    Added_SV_Position->AppendSemanticIndex(0);
    Added_SV_Position->SetKind(hlsl::DXIL::SemanticKind::Position);
    // AppendElement sets the element's ID by default
    auto index = InputSignature.AppendElement(std::move(Added_SV_Position));
    return InputElements[index]->GetID();
  } else {
    return Existing_SV_Position->get()->GetID();
  }
}

void ForEachDynamicallyIndexedResource(
    hlsl::DxilModule &DM,
    const std::function<bool(bool, Instruction *, Value *)> &Visitor) {
  OP *HlslOP = DM.GetOP();
  LLVMContext &Ctx = DM.GetModule()->getContext();

  for (llvm::Function &F : DM.GetModule()->functions()) {
    if (F.isDeclaration() && !F.use_empty() && OP::IsDxilOpFunc(&F)) {
      if (F.hasName()) {
        if (F.getName().find("createHandleForLib") != StringRef::npos) {
          auto FunctionUses = F.uses();
          for (auto FI = FunctionUses.begin(); FI != FunctionUses.end();) {
            auto &FunctionUse = *FI++;
            auto FunctionUser = FunctionUse.getUser();
            auto instruction = cast<Instruction>(FunctionUser);
            Value *resourceLoad = instruction->getOperand(
                DXIL::OperandIndex::kCreateHandleForLibResOpIdx);
            if (auto *load = cast<LoadInst>(resourceLoad)) {
              auto *resOrGep = load->getOperand(0);
              if (auto *gep = dyn_cast<GetElementPtrInst>(resOrGep)) {
                if (!Visitor(DxilMDHelper::IsMarkedNonUniform(gep), load,
                             gep->getOperand(2))) {
                  return;
                }
              }
            }
          }
        }
      }
    }
  }

  auto CreateHandleFn =
      HlslOP->GetOpFunc(DXIL::OpCode::CreateHandle, Type::getVoidTy(Ctx));
  auto CreateHandleFromBindingFn = HlslOP->GetOpFunc(
      DXIL::OpCode::CreateHandleFromBinding, Type::getVoidTy(Ctx));
  auto CreateHandleFromHeapFn = HlslOP->GetOpFunc(
      DXIL::OpCode::CreateHandleFromHeap, Type::getVoidTy(Ctx));

  struct UnusedDeclarationCleanup {
    hlsl::DxilModule &DM;
    llvm::Function *CreateHandleFn;
    llvm::Function *CreateHandleFromBindingFn;
    llvm::Function *CreateHandleFromHeapFn;
    ~UnusedDeclarationCleanup() {
      EraseIfUnused(DM, CreateHandleFn);
      EraseIfUnused(DM, CreateHandleFromBindingFn);
      EraseIfUnused(DM, CreateHandleFromHeapFn);
    }
  } cleanup{DM, CreateHandleFn, CreateHandleFromBindingFn,
            CreateHandleFromHeapFn};

  for (auto FI = CreateHandleFn->user_begin();
       FI != CreateHandleFn->user_end();) {
    auto *FunctionUser = *FI++;
    auto instruction = cast<Instruction>(FunctionUser);
    Value *index =
        instruction->getOperand(DXIL::OperandIndex::kCreateHandleResIndexOpIdx);
    if (!isa<Constant>(index)) {
      const DxilInst_CreateHandle createHandle(instruction);
      if (!Visitor(createHandle.get_nonUniformIndex_val(), instruction,
                   index)) {
        return;
      }
    }
  }

  for (auto FI = CreateHandleFromBindingFn->user_begin();
       FI != CreateHandleFromBindingFn->user_end();) {
    auto *FunctionUser = *FI++;
    auto instruction = cast<Instruction>(FunctionUser);
    Value *index = instruction->getOperand(
        DXIL::OperandIndex::kCreateHandleFromBindingResIndexOpIdx);
    if (!isa<Constant>(index)) {
      const DxilInst_CreateHandleFromBinding createHandle(instruction);
      if (!Visitor(createHandle.get_nonUniformIndex_val(), instruction,
                   index)) {
        return;
      }
    }
  }

  for (auto FI = CreateHandleFromHeapFn->user_begin();
       FI != CreateHandleFromHeapFn->user_end();) {
    auto *FunctionUser = *FI++;
    auto instruction = cast<Instruction>(FunctionUser);
    Value *index = instruction->getOperand(
        DXIL::OperandIndex::kCreateHandleFromHeapHeapIndexOpIdx);
    if (!isa<Constant>(index)) {
      const DxilInst_CreateHandleFromHeap createHandle(instruction);
      if (!Visitor(createHandle.get_nonUniformIndex_val(), instruction,
                   index)) {
        return;
      }
    }
  }
}

#ifdef PIX_DEBUG_DUMP_HELPER

static int g_logIndent = 0;
void IncreaseLogIndent() { g_logIndent++; }
void DecreaseLogIndent() { --g_logIndent; }

void Log(const char *format, ...) {
  va_list argumentPointer;
  va_start(argumentPointer, format);
  char buffer[512];
  vsnprintf(buffer, _countof(buffer), format, argumentPointer);
  va_end(argumentPointer);
  for (int i = 0; i < g_logIndent; ++i) {
    OutputDebugFormatA("    ");
  }
  OutputDebugFormatA(buffer);
  OutputDebugFormatA("\n");
}

void LogPartialLine(const char *format, ...) {
  va_list argumentPointer;
  va_start(argumentPointer, format);
  char buffer[512];
  vsnprintf(buffer, _countof(buffer), format, argumentPointer);
  va_end(argumentPointer);
  for (int i = 0; i < g_logIndent; ++i) {
    OutputDebugFormatA("    ");
  }
  OutputDebugFormatA(buffer);
}

static llvm::DIType const *DITypePeelTypeAlias(llvm::DIType const *Ty) {
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    const llvm::DITypeIdentifierMap EmptyMap;
    switch (DerivedTy->getTag()) {
    case llvm::dwarf::DW_TAG_restrict_type:
    case llvm::dwarf::DW_TAG_reference_type:
    case llvm::dwarf::DW_TAG_const_type:
    case llvm::dwarf::DW_TAG_typedef:
    case llvm::dwarf::DW_TAG_pointer_type:
    case llvm::dwarf::DW_TAG_member:
      return DITypePeelTypeAlias(DerivedTy->getBaseType().resolve(EmptyMap));
    }
  }

  return Ty;
}

void DumpArrayType(llvm::DICompositeType const *Ty);
void DumpStructType(llvm::DICompositeType const *Ty);

void DumpFullType(llvm::DIType const *type) {
  auto *Ty = DITypePeelTypeAlias(type);

  const llvm::DITypeIdentifierMap EmptyMap;
  if (auto *DerivedTy = llvm::dyn_cast<llvm::DIDerivedType>(Ty)) {
    switch (DerivedTy->getTag()) {
    default:
      assert(!"Unhandled DIDerivedType");
      std::abort();
      return;
    case llvm::dwarf::DW_TAG_arg_variable: // "this" pointer
    case llvm::dwarf::DW_TAG_pointer_type: // "this" pointer
    case llvm::dwarf::DW_TAG_restrict_type:
    case llvm::dwarf::DW_TAG_reference_type:
    case llvm::dwarf::DW_TAG_const_type:
    case llvm::dwarf::DW_TAG_typedef:
    case llvm::dwarf::DW_TAG_inheritance:
      DumpFullType(DerivedTy->getBaseType().resolve(EmptyMap));
      return;
    case llvm::dwarf::DW_TAG_member: {
      Log("Member variable");
      ScopedIndenter indent;
      DumpFullType(DerivedTy->getBaseType().resolve(EmptyMap));
    }
      return;
    case llvm::dwarf::DW_TAG_subroutine_type:
      std::abort();
      return;
    }
  } else if (auto *CompositeTy = llvm::dyn_cast<llvm::DICompositeType>(Ty)) {
    switch (CompositeTy->getTag()) {
    default:
      assert(!"Unhandled DICompositeType");
      std::abort();
      return;
    case llvm::dwarf::DW_TAG_array_type:
      DumpArrayType(CompositeTy);
      return;
    case llvm::dwarf::DW_TAG_structure_type:
    case llvm::dwarf::DW_TAG_class_type:
      DumpStructType(CompositeTy);
      return;
    case llvm::dwarf::DW_TAG_enumeration_type:
      // enum base type is int:
      std::abort();
      return;
    }
  } else if (auto *BasicTy = llvm::dyn_cast<llvm::DIBasicType>(Ty)) {
    Log("%d: %s", BasicTy->getOffsetInBits(), BasicTy->getName().str().c_str());
    return;
  } else {
    std::abort();
  }
}

static unsigned NumArrayElements(llvm::DICompositeType const *Array) {
  if (Array->getElements().size() == 0) {
    return 0;
  }

  unsigned NumElements = 1;
  for (llvm::DINode *N : Array->getElements()) {
    if (auto *Subrange = llvm::dyn_cast<llvm::DISubrange>(N)) {
      NumElements *= Subrange->getCount();
    } else {
      assert(!"Unhandled array element");
      return 0;
    }
  }
  return NumElements;
}

void DumpArrayType(llvm::DICompositeType const *Ty) {
  unsigned NumElements = NumArrayElements(Ty);
  Log("Array %s: size: %d", Ty->getName().str().c_str(), NumElements);
  if (NumElements == 0) {
    std::abort();
    return;
  }

  const llvm::DITypeIdentifierMap EmptyMap;
  llvm::DIType *ElementTy = Ty->getBaseType().resolve(EmptyMap);
  ScopedIndenter indent;
  DumpFullType(ElementTy);
}

void DumpStructType(llvm::DICompositeType const *Ty) {
  Log("Struct %s", Ty->getName().str().c_str());
  ScopedIndenter indent;
  auto Elements = Ty->getElements();
  if (Elements.begin() == Elements.end()) {
    Log("Resource member: size %d", Ty->getSizeInBits());
    return;
  }
  for (auto *Element : Elements) {
    switch (Element->getTag()) {
    case llvm::dwarf::DW_TAG_member: {
      if (auto *Member = llvm::dyn_cast<llvm::DIDerivedType>(Element)) {
        DumpFullType(Member);
        break;
      }
      assert(!"member is not a Member");
      std::abort();
      return;
    }
    case llvm::dwarf::DW_TAG_subprogram: {
      if (auto *SubProgram = llvm::dyn_cast<llvm::DISubprogram>(Element)) {
        Log("Member function %s", SubProgram->getName().str().c_str());
        continue;
      }
      assert(!"DISubprogram not understood");
      std::abort();
      return;
    }
    case llvm::dwarf::DW_TAG_inheritance: {
      if (auto *Member = llvm::dyn_cast<llvm::DIDerivedType>(Element)) {
        DumpFullType(Member);
      } else {
        std::abort();
      }
      continue;
    }
    default:
      assert(!"Unhandled field type in DIStructType");
      std::abort();
    }
  }
}
#endif
} // namespace PIXPassHelpers
