#include "dxc/Support/WinIncludes.h"
#include <dxc/Support/Global.h> // for hresult handling with DXC_FAILED
#include <filesystem>           // C++17 and later
// WinIncludes must come before dxcapi.extval.h
#include "dxc/Support/dxcapi.extval.h"
#include "dxc/Support/microcom.h"

std::vector<LPCWSTR> AddVDCompilationArg(UINT32 ArgCount, LPCWSTR *pArguments) {
  UINT32 newArgCount = ArgCount + 1;
  std::vector<LPCWSTR> newArgs;
  newArgs.reserve(newArgCount);

  // Copy existing args
  for (unsigned int i = 0; i < ArgCount; ++i) {
    newArgs.push_back(pArguments[i]);
  }

  // Add an extra argument
  newArgs.push_back(L"-Vd");
  return newArgs;
}

namespace dxc {

class ExternalValidationWrapper : public IDxcCompiler,
                                  public IDxcCompiler3,
                                  public IDxcValidator2 {
  DXC_MICROCOM_REF_FIELD(RefCount);

  CComPtr<IUnknown> Compiler;
  CComPtr<IUnknown> Validator;

public:
  DXC_MICROCOM_ADDREF_RELEASE_IMPL(RefCount);

  ExternalValidationWrapper(IUnknown *Compiler, IUnknown *Validator)
      : Compiler(Compiler), Validator(Validator) {}

  HRESULT STDMETHODCALLTYPE QueryInterface(REFIID IID, void **Object) override {
    if (IsEqualIID(IID, _uuidof(IUnknown))) {
      // For IUnknown we need to pick one of the various ones we've picked up
      // through multiple interfaces; which one doesn't really matter.
      *Object = static_cast<IDxcCompiler *>(this);
      AddRef();
      return S_OK;
    }

    // Check for interfaces that wrap the compiler
    if (SUCCEEDED(QueryWrappedInterface<IDxcCompiler>(Compiler, Object)))
      return S_OK;

    if (SUCCEEDED(QueryWrappedInterface<IDxcCompiler3>(Compiler, Object)))
      return S_OK;

    // Check for interfaces that wrap the validator
    if (SUCCEEDED(QueryWrappedInterface<IDxcValidator>(Validator, Object)))
      return S_OK;

    if (SUCCEEDED(QueryWrappedInterface<IDxcValidator2>(Validator, Object)))
      return S_OK;

    return E_NOINTERFACE;
  }

  // IDxcCompiler
  HRESULT STDMETHODCALLTYPE Compile(IDxcBlob *pSource, LPCWSTR pSourceName,
                                    LPCWSTR pEntryPoint, LPCWSTR pTargetProfile,
                                    LPCWSTR *pArguments, UINT32 argCount,
                                    const DxcDefine *pDefines,
                                    UINT32 defineCount,
                                    IDxcIncludeHandler *pIncludeHandler,
                                    IDxcOperationResult **ppResult) override {
    CComPtr<IDxcCompiler> DxcCompiler;
    HRESULT Hr = Compiler.QueryInterface(&DxcCompiler);
    if (FAILED(Hr))
      return Hr;

    // First, add -Vd to the compilation args, to disable the
    // internal validator
    std::vector<LPCWSTR> newArgs = AddVDCompilationArg(argCount, pArguments);
    return DxcCompiler->Compile(
        pSource, pSourceName, pEntryPoint, pTargetProfile, newArgs.data(),
        newArgs.size(), pDefines, defineCount, pIncludeHandler, ppResult);
  }

  HRESULT STDMETHODCALLTYPE
  Preprocess(IDxcBlob *pSource, LPCWSTR pSourceName, LPCWSTR *pArguments,
             UINT32 argCount, const DxcDefine *pDefines, UINT32 defineCount,
             IDxcIncludeHandler *pIncludeHandler,
             IDxcOperationResult **ppResult) override {
    CComPtr<IDxcCompiler> DxcCompiler;
    HRESULT Hr = Compiler.QueryInterface(&DxcCompiler);
    if (FAILED(Hr))
      return Hr;

    return DxcCompiler->Preprocess(pSource, pSourceName, pArguments, argCount,
                                   pDefines, defineCount, pIncludeHandler,
                                   ppResult);
  }

  HRESULT STDMETHODCALLTYPE
  Disassemble(IDxcBlob *pSource, IDxcBlobEncoding **ppDisassembly) override {
    CComPtr<IDxcCompiler> DxcCompiler;
    HRESULT Hr = Compiler.QueryInterface(&DxcCompiler);
    if (FAILED(Hr))
      return Hr;

    return DxcCompiler->Disassemble(pSource, ppDisassembly);
  }

  // IDxcCompiler3
  HRESULT STDMETHODCALLTYPE Compile(const DxcBuffer *pSource,
                                    LPCWSTR *pArguments, UINT32 argCount,
                                    IDxcIncludeHandler *pIncludeHandler,
                                    REFIID riid, LPVOID *ppResult) override {
    CComPtr<IDxcCompiler3> DxcCompiler3;
    HRESULT Hr = Compiler.QueryInterface(&DxcCompiler3);
    if (FAILED(Hr))
      return Hr;

    // First, add -Vd to the compilation args, to disable the
    // internal validator
    std::vector<LPCWSTR> newArgs = AddVDCompilationArg(argCount, pArguments);
    return DxcCompiler3->Compile(pSource, newArgs.data(), newArgs.size(),
                                 pIncludeHandler, riid, ppResult);
  }

  HRESULT STDMETHODCALLTYPE Disassemble(const DxcBuffer *pObject, REFIID riid,
                                        LPVOID *ppResult) override {
    CComPtr<IDxcCompiler3> DxcCompiler3;
    HRESULT Hr = Compiler.QueryInterface(&DxcCompiler3);
    if (FAILED(Hr))
      return Hr;

    return DxcCompiler3->Disassemble(pObject, riid, ppResult);
  }

  // IDxcValidator
  HRESULT STDMETHODCALLTYPE Validate(IDxcBlob *pShader, UINT32 Flags,
                                     IDxcOperationResult **ppResult) override {
    CComPtr<IDxcValidator> DxcValidator;
    HRESULT Hr = Validator.QueryInterface(&DxcValidator);
    if (FAILED(Hr))
      return Hr;

    return DxcValidator->Validate(pShader, Flags, ppResult);
  }

  // IDxcValidator2
  HRESULT STDMETHODCALLTYPE ValidateWithDebug(
      IDxcBlob *pShader, UINT32 Flags, DxcBuffer *pOptDebugBitcode,
      IDxcOperationResult **ppResult) override {
    CComPtr<IDxcValidator2> DxcValidator2;
    HRESULT Hr = Validator.QueryInterface(&DxcValidator2);
    if (FAILED(Hr))
      return Hr;

    return DxcValidator2->ValidateWithDebug(pShader, Flags, pOptDebugBitcode,
                                            ppResult);
  }

private:
  template <typename T>
  HRESULT QueryWrappedInterface(IUnknown *Wrapped, void **Object) {
    if (SupportsInterface(_uuidof(T), Wrapped)) {
      *Object = static_cast<T *>(this);
      AddRef();
      return S_OK;
    }
    return E_NOINTERFACE;
  }

  static bool SupportsInterface(REFIID IID, IUnknown *Object) {
    CComPtr<IUnknown> O;

    if (SUCCEEDED(Object->QueryInterface(IID, reinterpret_cast<void **>(&O))))
      return true;

    return false;
  }
};

HRESULT DxcDllExtValidationLoader::CreateInstanceImpl(REFCLSID clsid,
                                                      REFIID riid,
                                                      IUnknown **pResult) {
  if (pResult == nullptr)
    return E_POINTER;

  *pResult = nullptr;

  // If there is intent to use an external dxil.dll
  if (!DxilDllPath.empty() && !DxilDllFailedToLoad()) {
    if (clsid == CLSID_DxcCompiler) {
      HRESULT Hr = E_UNEXPECTED;

      // Create compiler
      CComPtr<IUnknown> Compiler;
      Hr = DxCompilerSupport.CreateInstance<IUnknown>(CLSID_DxcCompiler,
                                                      &Compiler);
      if (FAILED(Hr))
        return Hr;

      // Create validator
      CComPtr<IUnknown> Validator;
      Hr = DxilExtValSupport.CreateInstance<IUnknown>(CLSID_DxcValidator,
                                                      &Validator);
      if (FAILED(Hr))
        return Hr;

      CComPtr<ExternalValidationWrapper> Wrapper(
          new (std::nothrow) ExternalValidationWrapper(Compiler, Validator));
      return Wrapper->QueryInterface(riid, reinterpret_cast<void **>(pResult));
    }
  }
  // Fallback: let DxCompiler handle it
  return DxCompilerSupport.CreateInstance(clsid, riid, pResult);
}

HRESULT DxcDllExtValidationLoader::CreateInstance2Impl(IMalloc *pMalloc,
                                                       REFCLSID clsid,
                                                       REFIID riid,
                                                       IUnknown **pResult) {
  if (pResult == nullptr)
    return E_POINTER;

  *pResult = nullptr;

  if (pResult == nullptr)
    return E_POINTER;

  *pResult = nullptr;

  // If there is intent to use an external dxil.dll
  if (!DxilDllPath.empty() && !DxilDllFailedToLoad()) {
    if (clsid == CLSID_DxcCompiler) {
      HRESULT Hr = E_UNEXPECTED;

      // Create compiler
      CComPtr<IUnknown> Compiler;
      Hr = DxCompilerSupport.CreateInstance2<IUnknown>(
          pMalloc, CLSID_DxcCompiler, &Compiler);
      if (FAILED(Hr))
        return Hr;

      // Create validator
      CComPtr<IUnknown> Validator;
      Hr = DxilExtValSupport.CreateInstance2<IUnknown>(
          pMalloc, CLSID_DxcValidator, &Validator);
      if (FAILED(Hr))
        return Hr;

      CComPtr<ExternalValidationWrapper> Wrapper(
          new (std::nothrow) ExternalValidationWrapper(Compiler, Validator));
      return Wrapper->QueryInterface(riid, reinterpret_cast<void **>(pResult));
    }
  }

  // Fallback: let DxCompiler handle it
  return DxCompilerSupport.CreateInstance2(pMalloc, clsid, riid, pResult);
}

HRESULT DxcDllExtValidationLoader::Initialize(llvm::raw_string_ostream &log) {
  // Load dxcompiler.dll
  HRESULT Result =
      DxCompilerSupport.InitializeForDll(kDxCompilerLib, "DxcCreateInstance");
  // if dxcompiler.dll fails to load, return the failed HRESULT
  if (DXC_FAILED(Result)) {
    log << "dxcompiler.dll failed to load";
    return Result;
  }

  // now handle external dxil.dll
  const char *EnvVarVal = std::getenv("DXC_DXIL_DLL_PATH");
  if (!EnvVarVal || std::string(EnvVarVal).empty()) {
    // no need to emit anything if external validation isn't wanted
    return S_OK;
  }

  DxilDllPath = std::string(EnvVarVal);
  std::filesystem::path DllPath(DxilDllPath);

  // Check if path is absolute and exists
  if (!DllPath.is_absolute() || !std::filesystem::exists(DllPath)) {
    log << "dxil.dll path " << DxilDllPath << " could not be found";
    return E_INVALIDARG;
  }

  log << "Loading external dxil.dll from " << DxilDllPath;
  Result = DxilExtValSupport.InitializeForDll(DxilDllPath.c_str(),
                                              "DxcCreateInstance");
  if (DXC_FAILED(Result)) {
    log << "dxil.dll failed to load";
    return Result;
  }

  return Result;
}

} // namespace dxc
