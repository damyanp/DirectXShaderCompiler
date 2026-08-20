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
; shader hash: 045d381bbf8f60bd273cf7ee431da2af
;
; Pipeline Runtime Information: 
;
;PSVRuntimeInfo:
; Amplification Shader
; NumThreads=(1,1,1)
; NumBytesGroupSharedMemory: 0
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
; EntryFunctionName: taskMain
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

%struct.S = type {}

define void @taskMain() {
  %1 = alloca %struct.S, align 1
  %2 = bitcast %struct.S* %1 to i8*
  call void @llvm.lifetime.start(i64 0, i8* %2) #0
  call void @dx.op.dispatchMesh.struct.S(i32 173, i32 1, i32 1, i32 1, %struct.S* nonnull %1)  ; DispatchMesh(threadGroupCountX,threadGroupCountY,threadGroupCountZ,payload)
  call void @llvm.lifetime.end(i64 0, i8* %2) #0
  ret void
}

; Function Attrs: nounwind
declare void @llvm.lifetime.start(i64, i8* nocapture) #0

; Function Attrs: nounwind
declare void @llvm.lifetime.end(i64, i8* nocapture) #0

; Function Attrs: nounwind
declare void @dx.op.dispatchMesh.struct.S(i32, i32, i32, i32, %struct.S*) #0

attributes #0 = { nounwind }

!llvm.ident = !{!0}
!dx.version = !{!1}
!dx.valver = !{!2}
!dx.shaderModel = !{!3}
!dx.entryPoints = !{!4}

!0 = !{!"dxc(private) 1.9.0.5465 (triage, 7665270b9)"}
!1 = !{i32 1, i32 6}
!2 = !{i32 1, i32 10}
!3 = !{!"as", i32 6, i32 6}
!4 = !{void ()* @taskMain, !"taskMain", null, null, !5}
!5 = !{i32 10, !6}
!6 = !{!7, i32 0}
!7 = !{i32 1, i32 1, i32 1}
