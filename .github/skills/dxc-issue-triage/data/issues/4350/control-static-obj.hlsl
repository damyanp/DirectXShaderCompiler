// NEGATIVE CONTROL for issue 4350.
// Identical to repro.hlsl except the object is `static`, so it is mutable rather
// than a file-scope (implicitly const, $Globals-backed) constant. There is no
// const violation, so the predicate must NOT fire. This proves `internal_failure`
// is not simply matching every compile of this shader shape.

struct MyStruct {
    int Idx;
    void Set() {
        Idx = 1;
    }
};

static MyStruct Obj;

void main()
{
    Obj.Set();
}
