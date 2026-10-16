; RUN: %dxopt %s -hlsl-passes-resume -hl-inline-single-use-entry-callees -verify -hlsl-hlemit -S | FileCheck %s

; Collapse the small helpers before the ordinary inliner sees the payload.
; Keep the shader entry and its input/output structure marshalling unchanged.

; CHECK-LABEL: define void @main(%Outputs* sret %output, %Inputs* %input)
; CHECK: call <2 x i32> @payload(
; CHECK: call void @llvm.memcpy
; CHECK: ret void
; CHECK-NOT: @outer
; CHECK-NOT: @inner
; CHECK-LABEL: define internal <2 x i32> @payload(
; CHECK: add <2 x i32>
; CHECK-LABEL: define <2 x i32> @other_caller(
; CHECK: call <2 x i32> @payload(
; CHECK-NOT: @outer
; CHECK-NOT: @inner

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%Inputs = type { <2 x i32>, i32 }
%Outputs = type { <2 x i32> }

define void @main(%Outputs* sret %output, %Inputs* %input) {
  %temp = alloca %Outputs
  %vp = getelementptr %Inputs, %Inputs* %input, i32 0, i32 0
  %sp = getelementptr %Inputs, %Inputs* %input, i32 0, i32 1
  %v = load <2 x i32>, <2 x i32>* %vp
  %s = load i32, i32* %sp
  %result = call <2 x i32> @outer(<2 x i32> %v, i32 %s)
  %field = getelementptr %Outputs, %Outputs* %temp, i32 0, i32 0
  store <2 x i32> %result, <2 x i32>* %field
  %dest = bitcast %Outputs* %output to i8*
  %source = bitcast %Outputs* %temp to i8*
  call void @llvm.memcpy.p0i8.p0i8.i32(i8* %dest, i8* %source, i32 8, i32 1, i1 false)
  ret void
}

define internal <2 x i32> @outer(<2 x i32> %v, i32 %s) #0 {
  %vcopy = alloca <2 x i32>
  %scopy = alloca i32
  store <2 x i32> %v, <2 x i32>* %vcopy
  store i32 %s, i32* %scopy
  %vload = load <2 x i32>, <2 x i32>* %vcopy
  %sload = load i32, i32* %scopy
  %result = call <2 x i32> @inner(<2 x i32> %vload, i32 %sload)
  ret <2 x i32> %result
}

define internal <2 x i32> @inner(<2 x i32> %v, i32 %s) #0 {
  %result = call <2 x i32> @payload(<2 x i32> %v, i32 %s)
  ret <2 x i32> %result
}

define internal <2 x i32> @payload(<2 x i32> %v, i32 %s) #0 {
  %result = add <2 x i32> %v, <i32 1, i32 2>
  ret <2 x i32> %result
}

define <2 x i32> @other_caller(<2 x i32> %v, i32 %s) {
  %result = call <2 x i32> @payload(<2 x i32> %v, i32 %s)
  ret <2 x i32> %result
}

declare void @llvm.memcpy.p0i8.p0i8.i32(i8*, i8*, i32, i32, i1)

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
!4 = !{void (%Outputs*, %Inputs*)* @main, !"main", null, null, null}
!5 = !{void (%Outputs*, %Inputs*)* @main, i32 5, i32 1, i32 1, i32 1}
!6 = !{i32 0}
