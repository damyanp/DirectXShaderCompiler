;
; Note: shader requires additional functionality:
;       Resource descriptor heap indexing
;
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
; OUT                      0   x           0     NONE    uint   x   
;
; shader hash: 6f46a9475501b98dcc255ab85ea2f14d
;
; Pipeline Runtime Information: 
;
;PSVRuntimeInfo:
; Vertex Shader
; OutputPositionPresent=0
; MinimumExpectedWaveLaneCount: 0
; MaximumExpectedWaveLaneCount: 4294967295
; UsesViewID: false
; SigInputElements: 0
; SigOutputElements: 1
; SigPatchConstOrPrimElements: 0
; SigInputVectors: 0
; SigOutputVectors[0]: 1
; SigOutputVectors[1]: 0
; SigOutputVectors[2]: 0
; SigOutputVectors[3]: 0
; EntryFunctionName: main
;
;
; Output signature:
;
; Name                 Index             InterpMode DynIdx
; -------------------- ----- ---------------------- ------
; OUT                      0        nointerpolation       
;
; Buffer Definitions:
;
;
; Resource Bindings:
;
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; ------------------------------ ---------- ------- ----------- ------- -------------- ------
;
;
; ViewId state:
;
; Number of inputs: 0, outputs: 1
; Outputs dependent on ViewId: {  }
; Inputs contributing to computation of Outputs:
;
target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%dx.types.Handle = type { i8* }
%dx.types.ResourceProperties = type { i32, i32 }
%dx.types.CBufRet.i32 = type { i32, i32, i32, i32 }

define void @main() {
  %1 = call %dx.types.Handle @dx.op.createHandleFromHeap(i32 218, i32 0, i1 false, i1 false)  ; CreateHandleFromHeap(index,samplerHeap,nonUniformIndex)
  %2 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle  zeroinitializer, %dx.types.ResourceProperties { i32 13, i32 4 })  ; AnnotateHandle(res,props)  resource: CBuffer
  %3 = call %dx.types.CBufRet.i32 @dx.op.cbufferLoadLegacy.i32(i32 59, %dx.types.Handle %2, i32 0)  ; CBufferLoadLegacy(handle,regIndex)
  %4 = extractvalue %dx.types.CBufRet.i32 %3, 0
  call void @dx.op.storeOutput.i32(i32 5, i32 0, i32 0, i8 0, i32 %4)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)
  ret void
}

; Function Attrs: nounwind
declare void @dx.op.storeOutput.i32(i32, i32, i32, i8, i32) #0

; Function Attrs: nounwind readnone
declare %dx.types.Handle @dx.op.createHandleFromHeap(i32, i32, i1, i1) #1

; Function Attrs: nounwind readonly
declare %dx.types.CBufRet.i32 @dx.op.cbufferLoadLegacy.i32(i32, %dx.types.Handle, i32) #2

; Function Attrs: nounwind readnone
declare %dx.types.Handle @dx.op.annotateHandle(i32, %dx.types.Handle, %dx.types.ResourceProperties) #1

attributes #0 = { nounwind }
attributes #1 = { nounwind readnone }
attributes #2 = { nounwind readonly }

!llvm.ident = !{!0}
!dx.version = !{!1}
!dx.valver = !{!2}
!dx.shaderModel = !{!3}
!dx.viewIdState = !{!4}
!dx.entryPoints = !{!5}

!0 = !{!"dxcoob 1.9.2602.24 (d355aa836)"}
!1 = !{i32 1, i32 6}
!2 = !{i32 1, i32 9}
!3 = !{!"vs", i32 6, i32 6}
!4 = !{[2 x i32] [i32 0, i32 1]}
!5 = !{void ()* @main, !"main", !6, null, !11}
!6 = !{null, !7, null}
!7 = !{!8}
!8 = !{i32 0, !"OUT", i8 5, i8 0, !9, i8 1, i32 1, i8 1, i32 0, i8 0, !10}
!9 = !{i32 0}
!10 = !{i32 3, i32 1}
!11 = !{i32 0, i64 1073741824}
