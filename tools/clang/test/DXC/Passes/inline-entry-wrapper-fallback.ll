; RUN: python -c "import sys; print(open(sys.argv[1]).read().replace('@selected',sys.argv[2]))" %s @shared > %t.ll
; RUN: %dxopt %t.ll -hlsl-passes-resume -hl-inline-entry-wrapper -verify -S | FileCheck %s -check-prefix=SHARED
; RUN: python -c "import sys; print(open(sys.argv[1]).read().replace('@selected',sys.argv[2]))" %s @address_taken > %t.ll
; RUN: %dxopt %t.ll -hlsl-passes-resume -hl-inline-entry-wrapper -verify -S | FileCheck %s -check-prefix=ADDRESS
; RUN: python -c "import sys; print(open(sys.argv[1]).read().replace('@selected',sys.argv[2]))" %s @exported > %t.ll
; RUN: %dxopt %t.ll -hlsl-passes-resume -hl-inline-entry-wrapper -verify -S | FileCheck %s -check-prefix=EXPORTED
; RUN: python -c "import sys; print(open(sys.argv[1]).read().replace('@selected',sys.argv[2]))" %s @noinline > %t.ll
; RUN: %dxopt %t.ll -hlsl-passes-resume -hl-inline-entry-wrapper -verify -S | FileCheck %s -check-prefix=NOINLINE
; RUN: python -c "import sys; print(open(sys.argv[1]).read().replace('@selected',sys.argv[2]))" %s @recursive > %t.ll
; RUN: %dxopt %t.ll -hlsl-passes-resume -hl-inline-entry-wrapper -verify -S | FileCheck %s -check-prefix=RECURSIVE
; RUN: python -c "import sys; print(open(sys.argv[1]).read().replace('@selected',sys.argv[2]))" %s @shader_root > %t.ll
; RUN: %dxopt %t.ll -hlsl-passes-resume -hl-inline-entry-wrapper -verify -S | FileCheck %s -check-prefix=ROOT

; Single-use callees are not inlined early when they are shared, address-taken,
; externally visible, noinline, recursive, or another shader root.
; SHARED-LABEL: define i32 @main(i32 %x)
; SHARED-NEXT: %result = call i32 @shared(i32 %x)
; SHARED-NEXT: ret i32 %result
; ADDRESS-LABEL: define i32 @main(i32 %x)
; ADDRESS-NEXT: %result = call i32 @address_taken(i32 %x)
; ADDRESS-NEXT: ret i32 %result
; EXPORTED-LABEL: define i32 @main(i32 %x)
; EXPORTED-NEXT: %result = call i32 @exported(i32 %x)
; EXPORTED-NEXT: ret i32 %result
; NOINLINE-LABEL: define i32 @main(i32 %x)
; NOINLINE-NEXT: %result = call i32 @noinline(i32 %x)
; NOINLINE-NEXT: ret i32 %result
; RECURSIVE-LABEL: define i32 @main(i32 %x)
; RECURSIVE-NEXT: %result = call i32 @recursive(i32 %x)
; RECURSIVE-NEXT: ret i32 %result
; ROOT-LABEL: define i32 @main(i32 %x)
; ROOT-NEXT: %result = call i32 @shader_root(i32 %x)
; ROOT-NEXT: ret i32 %result

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

@saved = global i32 (i32)* @address_taken

define i32 @main(i32 %x) {
  %result = call i32 @selected(i32 %x)
  ret i32 %result
}

define internal i32 @shared(i32 %x) #0 {
  %result = call i32 @payload(i32 %x)
  ret i32 %result
}

define i32 @other_caller(i32 %x) {
  %result = call i32 @shared(i32 %x)
  ret i32 %result
}

define internal i32 @address_taken(i32 %x) #0 {
  %result = call i32 @payload(i32 %x)
  ret i32 %result
}

define i32 @exported(i32 %x) #0 {
  %result = call i32 @payload(i32 %x)
  ret i32 %result
}

define internal i32 @noinline(i32 %x) #1 {
  %result = call i32 @payload(i32 %x)
  ret i32 %result
}

define internal i32 @recursive(i32 %x) #0 {
  %result = call i32 @recursive(i32 %x)
  ret i32 %result
}

define internal i32 @shader_root(i32 %x) #0 {
  %result = call i32 @payload(i32 %x)
  ret i32 %result
}

define internal i32 @payload(i32 %x) #0 {
  %result = mul i32 %x, %x
  ret i32 %result
}

attributes #0 = { alwaysinline nounwind }
attributes #1 = { noinline nounwind }

!pauseresume = !{!0}
!dx.version = !{!1}
!dx.valver = !{!2}
!dx.shaderModel = !{!3}
!dx.entryPoints = !{!4}
!dx.fnprops = !{!5, !7}
!dx.options = !{!6}

!0 = !{!"hlsl-hlemit", !"hlsl-hlensure"}
!1 = !{i32 1, i32 0}
!2 = !{i32 1, i32 8}
!3 = !{!"cs", i32 6, i32 0}
!4 = !{i32 (i32)* @main, !"main", null, null, null}
!5 = !{i32 (i32)* @main, i32 5, i32 1, i32 1, i32 1}
!6 = !{i32 0}
!7 = !{i32 (i32)* @shader_root, i32 5, i32 1, i32 1, i32 1}
