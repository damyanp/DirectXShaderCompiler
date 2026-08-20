; Hand-constructed DXIL: does validation reject a zeroinitializer/undef node
; handle fed straight into AnnotateNodeHandle (249) / AnnotateNodeRecordHandle
; (251), the same way it rejects one fed into GetNodeRecordPtr, OutputComplete
; or IncrementOutputCount (see tools/clang/test/DXILValidation/
; validate_undef_arg.ll, whose metadata skeleton this file reuses verbatim --
; same lib_6_8 node entry, same !dx.typeAnnotations / !dx.entryPoints shape --
; so that the only variable between the two files is which opcode receives
; the bad handle).

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%dx.types.NodeHandle = type { i8* }
%dx.types.NodeInfo = type { i32, i32 }
%dx.types.NodeRecordHandle = type { i8* }
%dx.types.NodeRecordInfo = type { i32, i32 }

define void @loadStress_16() {
  ; Never derived from CreateNodeOutputHandle.
  %1 = call %dx.types.NodeHandle @dx.op.annotateNodeHandle(i32 249, %dx.types.NodeHandle zeroinitializer, %dx.types.NodeInfo { i32 6, i32 24 })
  %2 = call %dx.types.NodeHandle @dx.op.annotateNodeHandle(i32 249, %dx.types.NodeHandle undef, %dx.types.NodeInfo { i32 6, i32 24 })

  ; Never derived from AllocateNodeOutputRecords.
  %3 = call %dx.types.NodeRecordHandle @dx.op.annotateNodeRecordHandle(i32 251, %dx.types.NodeRecordHandle zeroinitializer, %dx.types.NodeRecordInfo { i32 38, i32 24 })
  %4 = call %dx.types.NodeRecordHandle @dx.op.annotateNodeRecordHandle(i32 251, %dx.types.NodeRecordHandle undef, %dx.types.NodeRecordInfo { i32 38, i32 24 })

  ret void
}

; Function Attrs: nounwind readnone
declare %dx.types.NodeHandle @dx.op.annotateNodeHandle(i32, %dx.types.NodeHandle, %dx.types.NodeInfo) #0

; Function Attrs: nounwind readnone
declare %dx.types.NodeRecordHandle @dx.op.annotateNodeRecordHandle(i32, %dx.types.NodeRecordHandle, %dx.types.NodeRecordInfo) #0

attributes #0 = { nounwind readnone }

!llvm.ident = !{!0}
!dx.version = !{!1}
!dx.valver = !{!1}
!dx.shaderModel = !{!2}
!dx.typeAnnotations = !{!3}
!dx.entryPoints = !{!7, !8}

!0 = !{!"dxc(private) 1.7.0.4790 (work-graphs, 35d890870)"}
!1 = !{i32 1, i32 8}
!2 = !{!"lib", i32 6, i32 8}
!3 = !{i32 1, void ()* @loadStress_16, !4}
!4 = !{!5}
!5 = !{i32 0, !6, !6}
!6 = !{}
!7 = !{null, !"", null, null, null}
!8 = !{void ()* @loadStress_16, !"loadStress_16", null, null, !9}
!9 = !{i32 8, i32 15, i32 13, i32 1, i32 15, !10, i32 16, i32 -1, i32 22, !11, i32 20, !12, i32 21, !14, i32 4, !19, i32 5, !20}
!10 = !{!"loadStress_16", i32 0}
!11 = !{i32 3, i32 1, i32 1}
!12 = !{!13}
!13 = !{i32 1, i32 9}
!14 = !{!15}
!15 = !{i32 1, i32 6, i32 2, !16, i32 3, i32 0, i32 0, !18}
!16 = !{i32 0, i32 24, i32 1, !17}
!17 = !{i32 0, i32 5, i32 3}
!18 = !{!"loadStressChild", i32 0}
!19 = !{i32 1, i32 1, i32 1}
!20 = !{i32 0}
