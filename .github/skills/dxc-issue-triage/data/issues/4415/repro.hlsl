// RUN: %dxc -T vs_6_6 -E main %s

// Using CBV.u before defining CBV to a specific resource should result in error.
// It does result in a warning:
// warning: variable 'CBV' is uninitialized when used within its own initialization [-Wuninitialized]
// Should we make this warning an error by default?

// It also looks up the index with an invalid zeroinitializer handle in DXIL, which should cause a validation failure in any case:
// %1 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle zeroinitializer, %dx.types.ResourceProperties { i32 13, i32 4 })  ; AnnotateHandle(res,props)  resource: CBuffer

struct MyCB {
  uint u;
};
static ConstantBuffer<MyCB> CBV = ResourceDescriptorHeap[CBV.u];

uint main() : OUT {
  return CBV.u;
}
