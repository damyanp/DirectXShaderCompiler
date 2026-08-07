;
; Input signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; no parameters
;
; Output signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; no parameters
; shader hash: 380b6459e849743f215ccd37fc9fa976
;
; Pipeline Runtime Information: 
;
;PSVRuntimeInfo:
; Compute Shader
; NumThreads=(8,1,1)
; NumBytesGroupSharedMemory: 28
; MinimumExpectedWaveLaneCount: 0
; MaximumExpectedWaveLaneCount: 4294967295
; UsesViewID: false
; SigInputElements: 0
; SigOutputElements: 0
; SigPatchConstOrPrimElements: 0
; SigInputVectors: 0
; SigOutputVectors[0]: 0
; SigOutputVectors[1]: 0
; SigOutputVectors[2]: 0
; SigOutputVectors[3]: 0
; EntryFunctionName: main
;
;
; Buffer Definitions:
;
;
; Resource Bindings:
;
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; ------------------------------ ---------- ------- ----------- ------- -------------- ------
;
target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

@"\01?thingies@@3PAMA" = external addrspace(3) global [6 x float], align 4
@"\01?thingCounter@@3IA" = external addrspace(3) global i32, align 4

define void @main() {
  %1 = load i32, i32 addrspace(3)* @"\01?thingCounter@@3IA", align 4, !tbaa !7
  %2 = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %1
  %3 = load float, float addrspace(3)* %2, align 4, !tbaa !11
  %4 = fcmp fast ult float %3, 0.000000e+00
  br i1 %4, label %27, label %5

; <label>:5                                       ; preds = %0
  %6 = icmp sgt i32 %1, -1
  br i1 %6, label %7, label %25

; <label>:7                                       ; preds = %5
  %8 = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %1
  %9 = fcmp fast ugt float %3, 0.000000e+00
  br i1 %9, label %10, label %12

; <label>:10                                      ; preds = %7
  br label %14

; <label>:11                                      ; preds = %19
  br label %12

; <label>:12                                      ; preds = %11, %7
  %13 = phi float addrspace(3)* [ %8, %7 ], [ %22, %11 ]
  store float 3.000000e+00, float addrspace(3)* %13, align 4, !tbaa !11
  br label %25

; <label>:14                                      ; preds = %19, %10
  %15 = phi float addrspace(3)* [ %22, %19 ], [ %8, %10 ]
  %16 = phi i32 [ %17, %19 ], [ %1, %10 ]
  store float 4.000000e+00, float addrspace(3)* %15, align 4, !tbaa !11
  %17 = add nsw i32 %16, -1
  %18 = icmp sgt i32 %16, 0
  br i1 %18, label %19, label %24

; <label>:19                                      ; preds = %14
  %20 = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %17
  %21 = load float, float addrspace(3)* %20, align 4, !tbaa !11
  %22 = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %17
  %23 = fcmp fast ugt float %21, 0.000000e+00
  br i1 %23, label %14, label %11

; <label>:24                                      ; preds = %14
  br label %25

; <label>:25                                      ; preds = %24, %12, %5
  %26 = add i32 %1, 1
  store i32 %26, i32 addrspace(3)* @"\01?thingCounter@@3IA", align 4, !tbaa !7
  br label %27

; <label>:27                                      ; preds = %25, %0
  ret void
}

!llvm.ident = !{!0}
!dx.version = !{!1}
!dx.valver = !{!2}
!dx.shaderModel = !{!3}
!dx.entryPoints = !{!4}

!0 = !{!"dxc(private) 1.9.0.5433 (triage, ab5400907)"}
!1 = !{i32 1, i32 0}
!2 = !{i32 1, i32 10}
!3 = !{!"cs", i32 6, i32 0}
!4 = !{void ()* @main, !"main", null, null, !5}
!5 = !{i32 4, !6}
!6 = !{i32 8, i32 1, i32 1}
!7 = !{!8, !8, i64 0}
!8 = !{!"int", !9, i64 0}
!9 = !{!"omnipotent char", !10, i64 0}
!10 = !{!"Simple C/C++ TBAA"}
!11 = !{!12, !12, i64 0}
!12 = !{!"float", !9, i64 0}
