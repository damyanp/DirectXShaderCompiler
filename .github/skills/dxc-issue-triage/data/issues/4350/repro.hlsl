// From microsoft/DirectXShaderCompiler issue 4350, verbatim.
// Reporter's RUN line: %dxc -T vs_6_0 %s | FileCheck %s
// Reported: Internal Compiler error: llvm::cast<X>() argument of incompatible type!

struct MyStruct {
    int Idx;
    void Set() {
        Idx = 1;
    }
} Obj;

void main()
{
    Obj.Set();
}
