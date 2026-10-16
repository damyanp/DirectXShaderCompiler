// RUN: %dxc -E main -T ps_6_0 %s -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=INLINE
// RUN: %dxc -E main -T ps_6_0 %s -disable-lifetime-markers -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=INLINE
// RUN: %dxc -E main -T ps_6_0 %s -enable-lifetime-markers -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=INLINE
// RUN: %dxc -E main -T ps_6_0 %s -DPOINTER -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=INLINE
// RUN: %dxc -E main -T ps_6_0 %s -DENTRY_ARITHMETIC -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=INLINE
// RUN: %dxc -E main -T ps_6_0 %s -DSHARED -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=SHARED
// RUN: %dxc -E main -T ps_6_0 %s -Od -print-before verify -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=UNCHANGED
// RUN: %dxc -E main -T ps_6_0 %s -Zi -Qembed_debug -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=ZI
// RUN: %dxc -E main -T ps_6_0 %s -fcgl -print-before verify -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=UNCHANGED
// RUN: %dxc -E main -T ps_6_0 %s -fnew-inlining-behavior -print-before verify -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=UNCHANGED
// RUN: %dxc -T lib_6_3 %s -print-after hl-inline-single-use-entry-callees 2>&1 | FileCheck %s -check-prefix=LIBRARY

// INLINE: IR Dump After Inline eligible callees that have one call site, starting at the shader entry (hl-inline-single-use-entry-callees)
// INLINE-LABEL: define i32 @main(
// INLINE-NOT: call i32 {{.*}}outer
// INLINE-NOT: call i32 {{.*}}inner
// INLINE-NOT: call i32 {{.*}}payload
// INLINE: ret i32
// INLINE-NOT: define internal i32 {{.*}}outer
// INLINE-NOT: define internal i32 {{.*}}inner
// INLINE-NOT: define internal i32 {{.*}}payload
// INLINE: !DILocation({{.*}}inlinedAt:
// ZI: IR Dump After Inline eligible callees that have one call site, starting at the shader entry (hl-inline-single-use-entry-callees)
// ZI-LABEL: define i32 @main(
// ZI-NOT: call i32 {{.*}}outer
// ZI-NOT: call i32 {{.*}}inner
// ZI-NOT: call i32 {{.*}}payload
// ZI: ret i32
// ZI: !DILocation({{.*}}inlinedAt:
// SHARED: IR Dump After Inline eligible callees that have one call site, starting at the shader entry (hl-inline-single-use-entry-callees)
// SHARED-LABEL: define i32 @main(
// SHARED: call i32 {{.*}}payload
// SHARED: call i32 {{.*}}payload
// SHARED-NOT: define internal i32 {{.*}}outer
// SHARED-NOT: define internal i32 {{.*}}inner
// SHARED: define internal i32 {{.*}}payload
// UNCHANGED-NOT: {{^}}*** IR Dump After Inline eligible callees that have one call site, starting at the shader entry (hl-inline-single-use-entry-callees)
// UNCHANGED: define
// UNCHANGED-NOT: {{^}}*** IR Dump After Inline eligible callees that have one call site, starting at the shader entry (hl-inline-single-use-entry-callees)
// LIBRARY: IR Dump After Inline eligible callees that have one call site, starting at the shader entry (hl-inline-single-use-entry-callees)
// LIBRARY: define {{.*}}i32 {{.*}}outer
// LIBRARY: call i32 {{.*}}inner

uint payload(uint input) {
  return (input * 747796405u) ^ (input >> 7u);
}

uint inner(uint input) {
  return payload(input);
}

#ifdef POINTER
uint outer(inout uint input) {
#else
uint outer(uint input) {
#endif
  return inner(input);
}

uint main(uint input : TEXCOORD0) : SV_Target {
#ifdef ENTRY_ARITHMETIC
  return outer(input + 1);
#elif defined(SHARED)
  return outer(input) + payload(input + 1);
#else
  return outer(input);
#endif
}
