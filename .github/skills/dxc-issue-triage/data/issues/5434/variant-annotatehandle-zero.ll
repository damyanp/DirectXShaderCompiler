; Hand-constructed DXIL: does validation reject a zeroinitializer/undef resource
; handle fed straight into AnnotateHandle (opcode 216), the same way it rejects
; one fed into an ordinary resource op such as WriteSamplerFeedbackLevel?
; See tools/clang/test/DXILValidation/validate_undef_arg.ll for the general-opcode
; positive control, and tools/clang/test/LitDXILValidation/
; createHandleFromBinding_non_constant_bind.ll for the AnnotateHandle/
; ResourceProperties shape this borrows.

target datalayout = "e-m:e-p:32:32-i1:32-i8:32-i16:32-i32:32-i64:64-f16:32-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%dx.types.Handle = type { i8* }
%dx.types.ResourceProperties = type { i32, i32 }

define void @main() {
  ; Never derived from any Create*Handle call -- the same kind of value that
  ; makes an ordinary resource op fail with "Instructions should not read
  ; uninitialized value."
  %1 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle zeroinitializer, %dx.types.ResourceProperties { i32 4107, i32 0 })  ; AnnotateHandle(res,props)  resource: RWByteAddressBuffer
  %2 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle undef, %dx.types.ResourceProperties { i32 4107, i32 0 })  ; AnnotateHandle(res,props)
  ret void
}

; Function Attrs: nounwind readnone
declare %dx.types.Handle @dx.op.annotateHandle(i32, %dx.types.Handle, %dx.types.ResourceProperties) #0

attributes #0 = { nounwind readnone }

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
