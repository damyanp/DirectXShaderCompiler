; Control for variant-annotatehandle-zero.ll: the identical zeroinitializer /
; undef %dx.types.Handle value, fed this time into an ordinary resource op
; (BufferUpdateCounter) instead of AnnotateHandle. Proves the general
; "handle never came from a Create*Handle call" check does fire when the
; consumer is not one of AnnotateHandle/AnnotateNodeHandle/
; AnnotateNodeRecordHandle/CreateHandleForLib -- isolating that the absence of
; a diagnostic in variant-annotatehandle-zero.ll is about the opcode, not
; about this %dx.types.Handle value being accepted everywhere.

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%dx.types.Handle = type { i8* }

define void @main() {
  %1 = call i32 @dx.op.bufferUpdateCounter(i32 70, %dx.types.Handle zeroinitializer, i8 1)  ; BufferUpdateCounter(uav,inc)
  %2 = call i32 @dx.op.bufferUpdateCounter(i32 70, %dx.types.Handle undef, i8 1)  ; BufferUpdateCounter(uav,inc)
  ret void
}

; Function Attrs: nounwind
declare i32 @dx.op.bufferUpdateCounter(i32, %dx.types.Handle, i8) #0

attributes #0 = { nounwind }

!llvm.ident = !{!0}
!dx.version = !{!1}
!dx.valver = !{!1}
!dx.shaderModel = !{!2}
!dx.entryPoints = !{!3}

!0 = !{!"dxc(private) 1.7.0.4790 (work-graphs, 35d890870)"}
!1 = !{i32 1, i32 8}
!2 = !{!"cs", i32 6, i32 8}
!3 = !{void ()* @main, !"main", null, null, !4}
!4 = !{i32 0, i64 8589934592, i32 4, !5}
!5 = !{i32 1, i32 1, i32 1}
