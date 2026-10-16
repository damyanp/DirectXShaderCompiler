; RUN: %dxopt %s -hlsl-passes-resume -hl-inline-single-use-entry-callees -verify -hlsl-hlemit -S | FileCheck %s

; CHECK-LABEL: define void @main()
; CHECK-NEXT: store i32 42, i32* @output
; CHECK-NEXT: ret void
; CHECK-NOT: @outer
; CHECK-NOT: @inner
; CHECK-NOT: @payload

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

@output = external global i32

define void @main() {
  call void @outer()
  ret void
}

define internal void @outer() #0 {
  call void @inner()
  ret void
}

define internal void @inner() #0 {
  call void @payload()
  ret void
}

define internal void @payload() #0 {
  store i32 42, i32* @output
  ret void
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
!4 = !{void ()* @main, !"main", null, null, null}
!5 = !{void ()* @main, i32 5, i32 1, i32 1, i32 1}
!6 = !{i32 0}
