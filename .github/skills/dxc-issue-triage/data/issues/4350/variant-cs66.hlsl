// Compute restating of issue 4350, published to Compiler Explorer.
//
// The unguarded arm is the maintainer's own restating of the issue, transcribed
// from the Compiler Explorer link in llvm-beanz's 2024-07-24 comment
// (https://godbolt.org/z/adMedG6xc): the same shader as repro.hlsl with a
// compute entry point instead of a vertex one. Compute is used so the Clang
// pane can participate -- Clang's pixel and vertex backends cannot lower
// signature I/O, so those stages fill a pane with noise about the stage.
//
// -DCONTROL_MUTABLE selects the CONTROL arm: the object becomes `static`, so it
// is mutable and there is no const violation. Everything else is identical.
// This is the control for the cross-compiler claim -- a compiler that rejects
// both arms is not diagnosing this issue, it is failing on HLSL.

struct MyStruct {
    int Idx;
    void Set() {
        Idx = 1;
    }
};

#ifdef CONTROL_MUTABLE
static MyStruct Obj;    // control: mutable, no const violation
#else
MyStruct Obj;           // file-scope: implicitly const, lives in $Globals
#endif

[numthreads(1,1,1)]
void main()
{
    Obj.Set();
}
