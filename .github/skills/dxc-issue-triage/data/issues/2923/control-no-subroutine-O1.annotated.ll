; ModuleID = 'control-no-subroutine-O1.annotated.bc'
target datalayout = "e-m:e-p:32:32-i1:32-i8:8-i16:16-i32:32-i64:64-f16:16-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%struct.smallPayload.0 = type { [3 x float], [3 x float] }

define void @main() {
entry:
  %0 = alloca [1 x float], i32 0, !pix-alloca-reg !39
  call void @llvm.dbg.declare(metadata [1 x float]* %0, metadata !40, metadata !45), !dbg !46 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %1 = alloca [1 x float], i32 0, !pix-alloca-reg !38
  call void @llvm.dbg.declare(metadata [1 x float]* %1, metadata !40, metadata !47), !dbg !46 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  %2 = alloca [1 x float], i32 0, !pix-alloca-reg !48
  call void @llvm.dbg.declare(metadata [1 x float]* %2, metadata !40, metadata !49), !dbg !46 ; var:"p" !DIExpression(DW_OP_bit_piece, 64, 32)
  %3 = alloca [1 x float], i32 0, !pix-alloca-reg !50
  call void @llvm.dbg.declare(metadata [1 x float]* %3, metadata !40, metadata !51), !dbg !46 ; var:"p" !DIExpression(DW_OP_bit_piece, 96, 32)
  %4 = alloca [1 x float], i32 0, !pix-alloca-reg !52
  call void @llvm.dbg.declare(metadata [1 x float]* %4, metadata !40, metadata !53), !dbg !46 ; var:"p" !DIExpression(DW_OP_bit_piece, 128, 32)
  %5 = alloca [1 x float], i32 0, !pix-alloca-reg !54
  call void @llvm.dbg.declare(metadata [1 x float]* %5, metadata !40, metadata !55), !dbg !46 ; var:"p" !DIExpression(DW_OP_bit_piece, 160, 32)
  %p1 = alloca %struct.smallPayload.0, align 8, !pix-alloca-reg !56
  %6 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 0, !dbg !57, !pix-dxil-reg !58, !pix-dxil-inst-num !59 ; line:16 col:11
  store float 1.000000e+00, float* %6, align 8, !dbg !57, !pix-dxil-inst-num !60, !pix-alloca-reg-write !61 ; line:16 col:11
  %7 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 1, !dbg !57, !pix-dxil-reg !58, !pix-dxil-inst-num !62 ; line:16 col:11
  store float 2.000000e+00, float* %7, align 4, !dbg !57, !pix-dxil-inst-num !63, !pix-alloca-reg-write !64 ; line:16 col:11
  %8 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 2, !dbg !57, !pix-dxil-reg !58, !pix-dxil-inst-num !65 ; line:16 col:11
  store float 3.000000e+00, float* %8, align 8, !dbg !57, !pix-dxil-inst-num !66, !pix-alloca-reg-write !67 ; line:16 col:11
  %9 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 0, !dbg !68, !pix-dxil-reg !69, !pix-dxil-inst-num !70 ; line:17 col:9
  store float 4.000000e+00, float* %9, align 4, !dbg !68, !pix-dxil-inst-num !71, !pix-alloca-reg-write !72 ; line:17 col:9
  %10 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 1, !dbg !68, !pix-dxil-reg !69, !pix-dxil-inst-num !73 ; line:17 col:9
  store float 5.000000e+00, float* %10, align 4, !dbg !68, !pix-dxil-inst-num !74, !pix-alloca-reg-write !75 ; line:17 col:9
  %11 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 2, !dbg !68, !pix-dxil-reg !69, !pix-dxil-inst-num !76 ; line:17 col:9
  store float 6.000000e+00, float* %11, align 4, !dbg !68, !pix-dxil-inst-num !77, !pix-alloca-reg-write !78 ; line:17 col:9
  %12 = load %struct.smallPayload.0, %struct.smallPayload.0* %p1, !dbg !79, !pix-dxil-inst-num !80 ; line:19 col:3
  %13 = extractvalue %struct.smallPayload.0 %12, 0, !pix-dxil-inst-num !81
  %14 = extractvalue [3 x float] %13, 0, !pix-dxil-reg !82, !pix-dxil-inst-num !83
  %15 = extractvalue [3 x float] %13, 1, !pix-dxil-reg !84, !pix-dxil-inst-num !85
  %16 = extractvalue [3 x float] %13, 2, !pix-dxil-reg !86, !pix-dxil-inst-num !87
  %17 = extractvalue %struct.smallPayload.0 %12, 1, !pix-dxil-inst-num !88
  %18 = extractvalue [3 x float] %17, 0, !pix-dxil-reg !89, !pix-dxil-inst-num !90
  %19 = extractvalue [3 x float] %17, 1, !pix-dxil-reg !91, !pix-dxil-inst-num !92
  %20 = extractvalue [3 x float] %17, 2, !pix-dxil-reg !93, !pix-dxil-inst-num !94
  %21 = getelementptr [1 x float], [1 x float]* %0, i32 0, i32 0, !pix-dxil-reg !95, !pix-dxil-inst-num !96
  store float %14, float* %21, !pix-dxil-inst-num !97, !pix-alloca-reg-write !98
  %22 = getelementptr [1 x float], [1 x float]* %1, i32 0, i32 0, !pix-dxil-reg !99, !pix-dxil-inst-num !100
  store float %15, float* %22, !pix-dxil-inst-num !101, !pix-alloca-reg-write !102
  %23 = getelementptr [1 x float], [1 x float]* %2, i32 0, i32 0, !pix-dxil-reg !103, !pix-dxil-inst-num !104
  store float %16, float* %23, !pix-dxil-inst-num !105, !pix-alloca-reg-write !106
  %24 = getelementptr [1 x float], [1 x float]* %3, i32 0, i32 0, !pix-dxil-reg !107, !pix-dxil-inst-num !108
  store float %18, float* %24, !pix-dxil-inst-num !109, !pix-alloca-reg-write !110
  %25 = getelementptr [1 x float], [1 x float]* %4, i32 0, i32 0, !pix-dxil-reg !111, !pix-dxil-inst-num !112
  store float %19, float* %25, !pix-dxil-inst-num !113, !pix-alloca-reg-write !114
  %26 = getelementptr [1 x float], [1 x float]* %5, i32 0, i32 0, !pix-dxil-reg !115, !pix-dxil-inst-num !116
  store float %20, float* %26, !pix-dxil-inst-num !117, !pix-alloca-reg-write !118
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* nonnull %p1), !dbg !79, !pix-dxil-inst-num !119 ; line:19 col:3
  ret void, !dbg !120, !pix-dxil-inst-num !121 ; line:20 col:1
}

; Function Attrs: nounwind
declare void @dx.op.dispatchMesh.struct.smallPayload.0(i32, i32, i32, i32, %struct.smallPayload.0*) #0

; Function Attrs: nounwind readnone
declare void @llvm.dbg.value(metadata, i64, metadata, metadata) #1

; Function Attrs: nounwind readnone
declare void @llvm.dbg.declare(metadata, metadata, metadata) #1

attributes #0 = { nounwind }
attributes #1 = { nounwind readnone }

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
!24 = !{!"-E", !"main", !"-T", !"as_6_5", !"-O1", !"-HV", !"2018", !"-enable-16bit-types", !"-Zi", !"-Qembed_debug", !"-Fo", !"control-no-subroutine-O1.dxo"}
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
!36 = !{i32 0, i64 8388608, i32 10, !37}
!37 = !{!38, i32 24}
!38 = !{i32 1, i32 1, i32 1}
!39 = !{i32 1, i32 0, i32 1}
!40 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "p", scope: !16, file: !1, line: 15, type: !41)
!41 = !DICompositeType(tag: DW_TAG_structure_type, name: "smallPayload", file: !1, line: 9, size: 192, align: 32, elements: !42)
!42 = !{!43, !44}
!43 = !DIDerivedType(tag: DW_TAG_member, name: "color", scope: !41, file: !1, line: 10, baseType: !4, size: 96, align: 32)
!44 = !DIDerivedType(tag: DW_TAG_member, name: "dir", scope: !41, file: !1, line: 11, baseType: !4, size: 96, align: 32, offset: 96)
!45 = !DIExpression(DW_OP_bit_piece, 0, 32)
!46 = !DILocation(line: 15, column: 16, scope: !16)
!47 = !DIExpression(DW_OP_bit_piece, 32, 32)
!48 = !{i32 1, i32 2, i32 1}
!49 = !DIExpression(DW_OP_bit_piece, 64, 32)
!50 = !{i32 1, i32 3, i32 1}
!51 = !DIExpression(DW_OP_bit_piece, 96, 32)
!52 = !{i32 1, i32 4, i32 1}
!53 = !DIExpression(DW_OP_bit_piece, 128, 32)
!54 = !{i32 1, i32 5, i32 1}
!55 = !DIExpression(DW_OP_bit_piece, 160, 32)
!56 = !{i32 1, i32 6, i32 6}
!57 = !DILocation(line: 16, column: 11, scope: !16)
!58 = !{i32 0, i32 6}
!59 = !{i32 3, i32 0}
!60 = !{i32 3, i32 1}
!61 = !{i32 2, !56, i32 1, i32 0}
!62 = !{i32 3, i32 2}
!63 = !{i32 3, i32 3}
!64 = !{i32 2, !56, i32 1, i32 1}
!65 = !{i32 3, i32 4}
!66 = !{i32 3, i32 5}
!67 = !{i32 2, !56, i32 1, i32 2}
!68 = !DILocation(line: 17, column: 9, scope: !16)
!69 = !{i32 0, i32 9}
!70 = !{i32 3, i32 6}
!71 = !{i32 3, i32 7}
!72 = !{i32 2, !56, i32 1, i32 3}
!73 = !{i32 3, i32 8}
!74 = !{i32 3, i32 9}
!75 = !{i32 2, !56, i32 1, i32 4}
!76 = !{i32 3, i32 10}
!77 = !{i32 3, i32 11}
!78 = !{i32 2, !56, i32 1, i32 5}
!79 = !DILocation(line: 19, column: 3, scope: !16)
!80 = !{i32 3, i32 12}
!81 = !{i32 3, i32 13}
!82 = !{i32 0, i32 12}
!83 = !{i32 3, i32 14}
!84 = !{i32 0, i32 13}
!85 = !{i32 3, i32 15}
!86 = !{i32 0, i32 14}
!87 = !{i32 3, i32 16}
!88 = !{i32 3, i32 17}
!89 = !{i32 0, i32 15}
!90 = !{i32 3, i32 18}
!91 = !{i32 0, i32 16}
!92 = !{i32 3, i32 19}
!93 = !{i32 0, i32 17}
!94 = !{i32 3, i32 20}
!95 = !{i32 0, i32 0}
!96 = !{i32 3, i32 21}
!97 = !{i32 3, i32 22}
!98 = !{i32 2, !39, i32 1, i32 0}
!99 = !{i32 0, i32 1}
!100 = !{i32 3, i32 23}
!101 = !{i32 3, i32 24}
!102 = !{i32 2, !38, i32 1, i32 0}
!103 = !{i32 0, i32 2}
!104 = !{i32 3, i32 25}
!105 = !{i32 3, i32 26}
!106 = !{i32 2, !48, i32 1, i32 0}
!107 = !{i32 0, i32 3}
!108 = !{i32 3, i32 27}
!109 = !{i32 3, i32 28}
!110 = !{i32 2, !50, i32 1, i32 0}
!111 = !{i32 0, i32 4}
!112 = !{i32 3, i32 29}
!113 = !{i32 3, i32 30}
!114 = !{i32 2, !52, i32 1, i32 0}
!115 = !{i32 0, i32 5}
!116 = !{i32 3, i32 31}
!117 = !{i32 3, i32 32}
!118 = !{i32 2, !54, i32 1, i32 0}
!119 = !{i32 3, i32 33}
!120 = !DILocation(line: 20, column: 1, scope: !16)
!121 = !{i32 3, i32 34}
