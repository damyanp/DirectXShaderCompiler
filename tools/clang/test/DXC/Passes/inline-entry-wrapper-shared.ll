; RUN: %dxopt %s -hlsl-passes-resume -hl-inline-entry-wrapper -verify -hlsl-hlemit -S | FileCheck %s

; Stop at a shared forwarder rather than changing either of its callers.
; CHECK-LABEL: define i32 @main(i32 %x)
; CHECK-NEXT: %result.i = call i32 @shared(i32 %x)
; CHECK-NEXT: ret i32 %result.i
; CHECK-NOT: @outer
; CHECK-LABEL: define internal i32 @shared(
; CHECK-NEXT: %result = call i32 @payload(i32 %x)
; CHECK-NEXT: ret i32 %result
; CHECK-LABEL: define i32 @other_caller(
; CHECK-NEXT: %result = call i32 @shared(i32 %x)
; CHECK-NOT: @outer

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

define i32 @main(i32 %x) {
  %result = call i32 @outer(i32 %x)
  ret i32 %result
}

define internal i32 @outer(i32 %x) #0 {
  %result = call i32 @shared(i32 %x)
  ret i32 %result
}

define internal i32 @shared(i32 %x) #0 {
  %result = call i32 @payload(i32 %x)
  ret i32 %result
}

define internal i32 @payload(i32 %x) #0 {
  %result = mul i32 %x, %x
  ret i32 %result
}

define i32 @other_caller(i32 %x) {
  %result = call i32 @shared(i32 %x)
  ret i32 %result
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
