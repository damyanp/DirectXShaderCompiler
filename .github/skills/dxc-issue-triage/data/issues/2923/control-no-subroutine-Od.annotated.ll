; ModuleID = 'control-no-subroutine-Od.annotated.bc'
target datalayout = "e-m:e-p:32:32-i1:32-i8:8-i16:16-i32:32-i64:64-f16:16-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%struct.smallPayload.0 = type { [3 x float], [3 x float] }

@dx.nothing.a = internal constant [1 x i32] zeroinitializer

define void @main() {
entry:
  %p1 = alloca %struct.smallPayload.0, !pix-alloca-reg !39
  call void @llvm.dbg.declare(metadata %struct.smallPayload.0* %p1, metadata !40, metadata !45), !dbg !46 ; var:"p" !DIExpression()
  %0 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !47, !pix-dxil-reg !48, !pix-dxil-inst-num !49 ; line:16 col:11
  %1 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 0, !dbg !47, !pix-dxil-reg !50, !pix-dxil-inst-num !51 ; line:16 col:11
  store float 1.000000e+00, float* %1, !dbg !47, !pix-dxil-inst-num !52, !pix-alloca-reg-write !53 ; line:16 col:11
  %2 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 1, !dbg !47, !pix-dxil-reg !50, !pix-dxil-inst-num !54 ; line:16 col:11
  store float 2.000000e+00, float* %2, !dbg !47, !pix-dxil-inst-num !55, !pix-alloca-reg-write !56 ; line:16 col:11
  %3 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 2, !dbg !47, !pix-dxil-reg !50, !pix-dxil-inst-num !57 ; line:16 col:11
  store float 3.000000e+00, float* %3, !dbg !47, !pix-dxil-inst-num !58, !pix-alloca-reg-write !59 ; line:16 col:11
  %4 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !60, !pix-dxil-reg !61, !pix-dxil-inst-num !62 ; line:17 col:9
  %5 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 0, !dbg !60, !pix-dxil-reg !63, !pix-dxil-inst-num !64 ; line:17 col:9
  store float 4.000000e+00, float* %5, !dbg !60, !pix-dxil-inst-num !65, !pix-alloca-reg-write !66 ; line:17 col:9
  %6 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 1, !dbg !60, !pix-dxil-reg !63, !pix-dxil-inst-num !67 ; line:17 col:9
  store float 5.000000e+00, float* %6, !dbg !60, !pix-dxil-inst-num !68, !pix-alloca-reg-write !69 ; line:17 col:9
  %7 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 2, !dbg !60, !pix-dxil-reg !63, !pix-dxil-inst-num !70 ; line:17 col:9
  store float 6.000000e+00, float* %7, !dbg !60, !pix-dxil-inst-num !71, !pix-alloca-reg-write !72 ; line:17 col:9
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* %p1), !dbg !73, !pix-dxil-inst-num !74 ; line:19 col:3
  %8 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !75, !pix-dxil-reg !76, !pix-dxil-inst-num !77 ; line:20 col:1
  ret void, !dbg !75, !pix-dxil-inst-num !78 ; line:20 col:1
}

; Function Attrs: nounwind readnone
declare void @llvm.dbg.declare(metadata, metadata, metadata) #0

; Function Attrs: nounwind
declare void @dx.op.dispatchMesh.struct.smallPayload.0(i32, i32, i32, i32, %struct.smallPayload.0*) #1

attributes #0 = { nounwind readnone }
attributes #1 = { nounwind }

!llvm.dbg.cu = !{!0}
!llvm.module.flags = !{!19, !20}
!llvm.ident = !{!21}
!dx.source.contents = !{!22}
!dx.source.defines = !{!2}
!dx.source.mainFileName = !{!23}
!dx.source.args = !{!24}
!dx.version = !{!25}
!dx.valver = !{!26}
!dx.shaderModel = !{!27}
!dx.typeAnnotations = !{!28, !32}
!dx.entryPoints = !{!35}

!0 = distinct !DICompileUnit(language: DW_LANG_C_plus_plus, file: !1, producer: "dxc(private) 1.9.0.5433 (triage, ab5400907)", isOptimized: false, runtimeVersion: 0, emissionKind: 1, enums: !2, retainedTypes: !3, subprograms: !15)
!1 = !DIFile(filename: "control-no-subroutine.hlsl", directory: "")
!2 = !{}
!3 = !{!4}
!4 = !DIDerivedType(tag: DW_TAG_typedef, name: "float3", file: !1, line: 15, baseType: !5)
!5 = !DICompositeType(tag: DW_TAG_class_type, name: "vector<float, 3>", file: !1, line: 15, size: 96, align: 32, elements: !6, templateParams: !11)
!6 = !{!7, !9, !10}
!7 = !DIDerivedType(tag: DW_TAG_member, name: "x", scope: !5, file: !1, line: 15, baseType: !8, size: 32, align: 32, flags: DIFlagPublic)
!8 = !DIBasicType(name: "float", size: 32, align: 32, encoding: DW_ATE_float)
!9 = !DIDerivedType(tag: DW_TAG_member, name: "y", scope: !5, file: !1, line: 15, baseType: !8, size: 32, align: 32, offset: 32, flags: DIFlagPublic)
!10 = !DIDerivedType(tag: DW_TAG_member, name: "z", scope: !5, file: !1, line: 15, baseType: !8, size: 32, align: 32, offset: 64, flags: DIFlagPublic)
!11 = !{!12, !13}
!12 = !DITemplateTypeParameter(name: "element", type: !8)
!13 = !DITemplateValueParameter(name: "element_count", type: !14, value: i32 3)
!14 = !DIBasicType(name: "int", size: 32, align: 32, encoding: DW_ATE_signed)
!15 = !{!16}
!16 = !DISubprogram(name: "main", scope: !1, file: !1, line: 14, type: !17, isLocal: false, isDefinition: true, scopeLine: 14, flags: DIFlagPrototyped, isOptimized: false, function: void ()* @main)
!17 = !DISubroutineType(types: !18)
!18 = !{null}
!19 = !{i32 2, !"Dwarf Version", i32 4}
!20 = !{i32 2, !"Debug Info Version", i32 3}
!21 = !{!"dxc(private) 1.9.0.5433 (triage, ab5400907)"}
!22 = !{!"control-no-subroutine.hlsl", !"// Control for microsoft/DirectXShaderCompiler#2923.\0D\0A//\0D\0A// PixTest.cpp's PixStructAnnotation_SequentialFloatN shader EXACTLY as it\0D\0A// stands in the tree (tools/clang/unittests/HLSL/PixTest.cpp:1889) -- no\0D\0A// subroutine. The test asserts that the PIX numbering pass gives this six\0D\0A// alloca registers and member offsets 0..5, so this is the known-good input\0D\0A// the symptom predicate must NOT fire on.\0D\0A\0D\0Astruct smallPayload {\0D\0A  float3 color;\0D\0A  float3 dir;\0D\0A};\0D\0A\0D\0A[numthreads(1, 1, 1)] void main() {\0D\0A  smallPayload p;\0D\0A  p.color = float3(1, 2, 3);\0D\0A  p.dir = float3(4, 5, 6);\0D\0A\0D\0A  DispatchMesh(1, 1, 1, p);\0D\0A}\0D\0A"}
!23 = !{!"control-no-subroutine.hlsl"}
!24 = !{!"-E", !"main", !"-T", !"as_6_5", !"-Od", !"-HV", !"2018", !"-enable-16bit-types", !"-Zi", !"-Qembed_debug", !"-Fo", !"control-no-subroutine-Od.dxo"}
!25 = !{i32 1, i32 5}
!26 = !{i32 1, i32 10}
!27 = !{!"as", i32 6, i32 5}
!28 = !{i32 0, %struct.smallPayload.0 undef, !29}
!29 = !{i32 0, !30, !31}
!30 = !{i32 6, !"color", i32 3, i32 0, i32 7, i32 9}
!31 = !{i32 6, !"dir", i32 3, i32 16, i32 7, i32 9}
!32 = !{i32 1, void ()* @main, !33}
!33 = !{!34}
!34 = !{i32 1, !2, !2}
!35 = !{void ()* @main, !"main", null, null, !36}
!36 = !{i32 0, i64 8388609, i32 10, !37}
!37 = !{!38, i32 24}
!38 = !{i32 1, i32 1, i32 1}
!39 = !{i32 1, i32 0, i32 6}
!40 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "p", scope: !16, file: !1, line: 15, type: !41)
!41 = !DICompositeType(tag: DW_TAG_structure_type, name: "smallPayload", file: !1, line: 9, size: 192, align: 32, elements: !42)
!42 = !{!43, !44}
!43 = !DIDerivedType(tag: DW_TAG_member, name: "color", scope: !41, file: !1, line: 10, baseType: !4, size: 96, align: 32)
!44 = !DIDerivedType(tag: DW_TAG_member, name: "dir", scope: !41, file: !1, line: 11, baseType: !4, size: 96, align: 32, offset: 96)
!45 = !DIExpression()
!46 = !DILocation(line: 15, column: 16, scope: !16)
!47 = !DILocation(line: 16, column: 11, scope: !16)
!48 = !{i32 0, i32 6}
!49 = !{i32 3, i32 0}
!50 = !{i32 0, i32 0}
!51 = !{i32 3, i32 1}
!52 = !{i32 3, i32 2}
!53 = !{i32 2, !39, i32 1, i32 0}
!54 = !{i32 3, i32 3}
!55 = !{i32 3, i32 4}
!56 = !{i32 2, !39, i32 1, i32 1}
!57 = !{i32 3, i32 5}
!58 = !{i32 3, i32 6}
!59 = !{i32 2, !39, i32 1, i32 2}
!60 = !DILocation(line: 17, column: 9, scope: !16)
!61 = !{i32 0, i32 7}
!62 = !{i32 3, i32 7}
!63 = !{i32 0, i32 3}
!64 = !{i32 3, i32 8}
!65 = !{i32 3, i32 9}
!66 = !{i32 2, !39, i32 1, i32 3}
!67 = !{i32 3, i32 10}
!68 = !{i32 3, i32 11}
!69 = !{i32 2, !39, i32 1, i32 4}
!70 = !{i32 3, i32 12}
!71 = !{i32 3, i32 13}
!72 = !{i32 2, !39, i32 1, i32 5}
!73 = !DILocation(line: 19, column: 3, scope: !16)
!74 = !{i32 3, i32 14}
!75 = !DILocation(line: 20, column: 1, scope: !16)
!76 = !{i32 0, i32 8}
!77 = !{i32 3, i32 15}
!78 = !{i32 3, i32 16}
