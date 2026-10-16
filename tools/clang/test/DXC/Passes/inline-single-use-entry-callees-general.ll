; RUN: %dxopt %s -hlsl-passes-resume -hl-inline-single-use-entry-callees -verify -S | FileCheck %s

; A single-use callee of the entry is inlined even when it does real work,
; and single-use callees exposed by that inlining are inlined in program order.
; Static allocas end up in the same order the bottom-up inliner produces.
; Shared callees are left for the regular inliner.

; CHECK-LABEL: define i32 @main(i32 %x)
; CHECK-NEXT: %second.slot.i = alloca i32
; CHECK-NEXT: %first.slot.i = alloca i32
; CHECK-NEXT: %inner.slot.i = alloca i32
; CHECK-NEXT: %main.slot = alloca i32
; CHECK: store i32 %v, i32* @output
; CHECK: call i32 @shared(
; CHECK: call i32 @shared(
; CHECK: ret i32
; CHECK-NOT: define internal i32 @inner(
; CHECK-NOT: define internal i32 @first(
; CHECK-NOT: define internal i32 @second(
; CHECK-LABEL: define internal i32 @shared(
; CHECK-LABEL: define i32 @other_caller(

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

@output = external global i32

define i32 @main(i32 %x) {
  %main.slot = alloca i32
  store i32 %x, i32* %main.slot
  %v = load i32, i32* %main.slot
  %condition = icmp eq i32 %v, 0
  br i1 %condition, label %zero, label %nonzero
zero:
  ret i32 0
nonzero:
  %result = call i32 @inner(i32 %v)
  ret i32 %result
}

define internal i32 @inner(i32 %x) #0 {
  %inner.slot = alloca i32
  store i32 %x, i32* @output
  store i32 %x, i32* %inner.slot
  %a = call i32 @first(i32 %x)
  %b = call i32 @shared(i32 %a)
  %c = call i32 @second(i32 %b)
  %d = load i32, i32* %inner.slot
  %e = add i32 %c, %d
  ret i32 %e
}

define internal i32 @first(i32 %x) #0 {
  %first.slot = alloca i32
  store i32 %x, i32* %first.slot
  %v = load i32, i32* %first.slot
  %r = mul i32 %v, 3
  ret i32 %r
}

define internal i32 @second(i32 %x) #0 {
  %second.slot = alloca i32
  store i32 %x, i32* %second.slot
  %v = load i32, i32* %second.slot
  %r = call i32 @shared(i32 %v)
  ret i32 %r
}

define internal i32 @shared(i32 %x) #0 {
  %r = xor i32 %x, 7
  ret i32 %r
}

define i32 @other_caller(i32 %x) {
  %r = call i32 @shared(i32 %x)
  ret i32 %r
}

attributes #0 = { alwaysinline nounwind }

!pauseresume = !{!0}
!dx.version = !{!1}
!dx.valver = !{!2}
!dx.shaderModel = !{!3}
!dx.entryPoints = !{!4}
!dx.fnprops = !{!5}
!dx.options = !{!6}

!0 = !{!"hlsl-hlemit", !"hlsl-hlensure"}
!1 = !{i32 1, i32 0}
!2 = !{i32 1, i32 8}
!3 = !{!"cs", i32 6, i32 0}
!4 = !{i32 (i32)* @main, !"main", null, null, null}
!5 = !{i32 (i32)* @main, i32 5, i32 1, i32 1, i32 1}
!6 = !{i32 0}
