// RUN: %dxc -T cs_6_0 -E main -DFUNC=mul -DDIM=4 %s  | FileCheck %s
// RUN: %dxc -T cs_6_0 -E main -DFUNC=mul -DDIM=3 %s  | FileCheck %s
// RUN: %dxc -T cs_6_0 -E main -DFUNC=mul -DDIM=2 %s  | FileCheck %s
// RUN: %dxc -T cs_6_0 -E main -DFUNC=dot -DDIM=4 %s  | FileCheck %s
// RUN: %dxc -T cs_6_0 -E main -DFUNC=dot -DDIM=3 %s  | FileCheck %s
// RUN: %dxc -T cs_6_0 -E main -DFUNC=dot -DDIM=2 %s  | FileCheck %s

// Verify that mul and dot of double vectors do not produce invalid DXIL Dot
// intrinsics (Dot2/3/4 only support half and float). Instead, the dot product
// should be expanded using FMul and FMad.
// %dxc runs validation, so the test implicitly verifies DXIL validity.

// CHECK-NOT: call double @dx.op.dot2.f64
// CHECK-NOT: call double @dx.op.dot3.f64
// CHECK-NOT: call double @dx.op.dot4.f64
// CHECK: fmul fast double
// CHECK: call double @dx.op.tertiary.f64(i32 46,

#if DIM == 4
typedef double4 DVec;
#elif DIM == 3
typedef double3 DVec;
#else
typedef double2 DVec;
#endif

RWStructuredBuffer<DVec> In;
RWStructuredBuffer<double> Out;

[numthreads(1, 1, 1)]
void main() {
    Out[0] = FUNC(In[0], In[1]);
}
