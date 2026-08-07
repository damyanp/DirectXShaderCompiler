; ModuleID = 'repro-O1.annotated.bc'
target datalayout = "e-m:e-p:32:32-i1:32-i8:8-i16:16-i32:32-i64:64-f16:16-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%struct.smallPayload.0 = type { [3 x float], [3 x float] }

define void @main() {
entry:
  %0 = alloca [1 x float], i32 0, !pix-alloca-reg !46
  call void @llvm.dbg.declare(metadata [1 x float]* %0, metadata !47, metadata !48), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %1 = alloca [1 x float], i32 0, !pix-alloca-reg !45
  call void @llvm.dbg.declare(metadata [1 x float]* %1, metadata !47, metadata !51), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  %2 = alloca [1 x float], i32 0, !pix-alloca-reg !52
  call void @llvm.dbg.declare(metadata [1 x float]* %2, metadata !47, metadata !53), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 64, 32)
  %3 = alloca [1 x float], i32 0, !pix-alloca-reg !54
  call void @llvm.dbg.declare(metadata [1 x float]* %3, metadata !47, metadata !55), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 96, 32)
  %4 = alloca [1 x float], i32 0, !pix-alloca-reg !56
  call void @llvm.dbg.declare(metadata [1 x float]* %4, metadata !47, metadata !57), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 128, 32)
  %5 = alloca [1 x float], i32 0, !pix-alloca-reg !58
  call void @llvm.dbg.declare(metadata [1 x float]* %5, metadata !47, metadata !59), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 160, 32)
  %6 = alloca [1 x float], i32 0, !pix-alloca-reg !60
  call void @llvm.dbg.declare(metadata [1 x float]* %6, metadata !61, metadata !48), !dbg !62 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %7 = alloca [1 x float], i32 0, !pix-alloca-reg !63
  call void @llvm.dbg.declare(metadata [1 x float]* %7, metadata !61, metadata !51), !dbg !62 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  %8 = alloca [1 x float], i32 0, !pix-alloca-reg !64
  call void @llvm.dbg.declare(metadata [1 x float]* %8, metadata !61, metadata !53), !dbg !62 ; var:"p" !DIExpression(DW_OP_bit_piece, 64, 32)
  %9 = alloca [1 x float], i32 0, !pix-alloca-reg !65
  call void @llvm.dbg.declare(metadata [1 x float]* %9, metadata !61, metadata !55), !dbg !62 ; var:"p" !DIExpression(DW_OP_bit_piece, 96, 32)
  %10 = alloca [1 x float], i32 0, !pix-alloca-reg !66
  call void @llvm.dbg.declare(metadata [1 x float]* %10, metadata !61, metadata !57), !dbg !62 ; var:"p" !DIExpression(DW_OP_bit_piece, 128, 32)
  %11 = alloca [1 x float], i32 0, !pix-alloca-reg !67
  call void @llvm.dbg.declare(metadata [1 x float]* %11, metadata !61, metadata !59), !dbg !62 ; var:"p" !DIExpression(DW_OP_bit_piece, 160, 32)
  %12 = alloca %struct.smallPayload.0, align 8, !dbg !49, !pix-alloca-reg !68 ; line:16 col:23
  %13 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %12, i32 0, i32 0, i32 0, !dbg !49, !pix-dxil-reg !69, !pix-dxil-inst-num !70 ; line:16 col:23
  store float 1.000000e+00, float* %13, align 8, !dbg !49, !pix-dxil-inst-num !71, !pix-alloca-reg-write !72 ; line:16 col:23
  %14 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %12, i32 0, i32 0, i32 1, !dbg !49, !pix-dxil-reg !69, !pix-dxil-inst-num !73 ; line:16 col:23
  store float 2.000000e+00, float* %14, align 4, !dbg !49, !pix-dxil-inst-num !74, !pix-alloca-reg-write !75 ; line:16 col:23
  %15 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %12, i32 0, i32 0, i32 2, !dbg !49, !pix-dxil-reg !69, !pix-dxil-inst-num !76 ; line:16 col:23
  store float 3.000000e+00, float* %15, align 8, !dbg !49, !pix-dxil-inst-num !77, !pix-alloca-reg-write !78 ; line:16 col:23
  %16 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %12, i32 0, i32 1, i32 0, !dbg !49, !pix-dxil-reg !79, !pix-dxil-inst-num !80 ; line:16 col:23
  store float 4.000000e+00, float* %16, align 4, !dbg !49, !pix-dxil-inst-num !81, !pix-alloca-reg-write !82 ; line:16 col:23
  %17 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %12, i32 0, i32 1, i32 1, !dbg !49, !pix-dxil-reg !79, !pix-dxil-inst-num !83 ; line:16 col:23
  store float 5.000000e+00, float* %17, align 4, !dbg !49, !pix-dxil-inst-num !84, !pix-alloca-reg-write !85 ; line:16 col:23
  %18 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %12, i32 0, i32 1, i32 2, !dbg !49, !pix-dxil-reg !79, !pix-dxil-inst-num !86 ; line:16 col:23
  store float 6.000000e+00, float* %18, align 4, !dbg !49, !pix-dxil-inst-num !87, !pix-alloca-reg-write !88 ; line:16 col:23
  %19 = load %struct.smallPayload.0, %struct.smallPayload.0* %12, !dbg !89, !pix-dxil-inst-num !90 ; line:16 col:28
  %20 = extractvalue %struct.smallPayload.0 %19, 0, !pix-dxil-inst-num !91
  %21 = extractvalue [3 x float] %20, 0, !pix-dxil-reg !92, !pix-dxil-inst-num !93
  %22 = extractvalue [3 x float] %20, 1, !pix-dxil-reg !94, !pix-dxil-inst-num !95
  %23 = extractvalue [3 x float] %20, 2, !pix-dxil-reg !96, !pix-dxil-inst-num !97
  %24 = extractvalue %struct.smallPayload.0 %19, 1, !pix-dxil-inst-num !98
  %25 = extractvalue [3 x float] %24, 0, !pix-dxil-reg !99, !pix-dxil-inst-num !100
  %26 = extractvalue [3 x float] %24, 1, !pix-dxil-reg !101, !pix-dxil-inst-num !102
  %27 = extractvalue [3 x float] %24, 2, !pix-dxil-reg !103, !pix-dxil-inst-num !104
  %28 = getelementptr [1 x float], [1 x float]* %0, i32 0, i32 0, !pix-dxil-reg !105, !pix-dxil-inst-num !106
  store float %21, float* %28, !pix-dxil-inst-num !107, !pix-alloca-reg-write !108
  %29 = getelementptr [1 x float], [1 x float]* %1, i32 0, i32 0, !pix-dxil-reg !109, !pix-dxil-inst-num !110
  store float %22, float* %29, !pix-dxil-inst-num !111, !pix-alloca-reg-write !112
  %30 = getelementptr [1 x float], [1 x float]* %2, i32 0, i32 0, !pix-dxil-reg !113, !pix-dxil-inst-num !114
  store float %23, float* %30, !pix-dxil-inst-num !115, !pix-alloca-reg-write !116
  %31 = getelementptr [1 x float], [1 x float]* %3, i32 0, i32 0, !pix-dxil-reg !117, !pix-dxil-inst-num !118
  store float %25, float* %31, !pix-dxil-inst-num !119, !pix-alloca-reg-write !120
  %32 = getelementptr [1 x float], [1 x float]* %4, i32 0, i32 0, !pix-dxil-reg !121, !pix-dxil-inst-num !122
  store float %26, float* %32, !pix-dxil-inst-num !123, !pix-alloca-reg-write !124
  %33 = getelementptr [1 x float], [1 x float]* %5, i32 0, i32 0, !pix-dxil-reg !125, !pix-dxil-inst-num !126
  store float %27, float* %33, !pix-dxil-inst-num !127, !pix-alloca-reg-write !128
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* nonnull %12), !dbg !89, !pix-dxil-inst-num !129 ; line:16 col:28
  ret void, !dbg !130, !pix-dxil-inst-num !131 ; line:24 col:1
}

; Function Attrs: nounwind readnone
declare void @llvm.dbg.value(metadata, i64, metadata, metadata) #0

; Function Attrs: nounwind
declare void @dx.op.dispatchMesh.struct.smallPayload.0(i32, i32, i32, i32, %struct.smallPayload.0*) #1

; Function Attrs: nounwind readnone
declare void @llvm.dbg.declare(metadata, metadata, metadata) #0

attributes #0 = { nounwind readnone }
attributes #1 = { nounwind }

!llvm.dbg.cu = !{!0}
!llvm.module.flags = !{!26, !27}
!llvm.ident = !{!28}
!dx.source.contents = !{!29}
!dx.source.defines = !{!2}
!dx.source.mainFileName = !{!30}
!dx.source.args = !{!31}
!dx.version = !{!32}
!dx.valver = !{!33}
!dx.shaderModel = !{!34}
!dx.typeAnnotations = !{!35, !39}
!dx.entryPoints = !{!42}

!0 = distinct !DICompileUnit(language: DW_LANG_C_plus_plus, file: !1, producer: "dxc(private) 1.9.0.5433 (triage, ab5400907)", isOptimized: false, runtimeVersion: 0, emissionKind: 1, enums: !2, retainedTypes: !3, subprograms: !15)
!1 = !DIFile(filename: "repro.hlsl", directory: "")
!2 = !{}
!3 = !{!4}
!4 = !DIDerivedType(tag: DW_TAG_typedef, name: "float3", file: !1, line: 19, baseType: !5)
!5 = !DICompositeType(tag: DW_TAG_class_type, name: "vector<float, 3>", file: !1, line: 19, size: 96, align: 32, elements: !6, templateParams: !11)
!6 = !{!7, !9, !10}
!7 = !DIDerivedType(tag: DW_TAG_member, name: "x", scope: !5, file: !1, line: 19, baseType: !8, size: 32, align: 32, flags: DIFlagPublic)
!8 = !DIBasicType(name: "float", size: 32, align: 32, encoding: DW_ATE_float)
!9 = !DIDerivedType(tag: DW_TAG_member, name: "y", scope: !5, file: !1, line: 19, baseType: !8, size: 32, align: 32, offset: 32, flags: DIFlagPublic)
!10 = !DIDerivedType(tag: DW_TAG_member, name: "z", scope: !5, file: !1, line: 19, baseType: !8, size: 32, align: 32, offset: 64, flags: DIFlagPublic)
!11 = !{!12, !13}
!12 = !DITemplateTypeParameter(name: "element", type: !8)
!13 = !DITemplateValueParameter(name: "element_count", type: !14, value: i32 3)
!14 = !DIBasicType(name: "int", size: 32, align: 32, encoding: DW_ATE_signed)
!15 = !{!16, !19}
!16 = !DISubprogram(name: "main", scope: !1, file: !1, line: 18, type: !17, isLocal: false, isDefinition: true, scopeLine: 18, flags: DIFlagPrototyped, isOptimized: false, function: void ()* @main)
!17 = !DISubroutineType(types: !18)
!18 = !{null}
!19 = !DISubprogram(name: "Sub", linkageName: "\01?Sub@@YAXUsmallPayload@@@Z", scope: !1, file: !1, line: 16, type: !20, isLocal: false, isDefinition: true, scopeLine: 16, flags: DIFlagPrototyped, isOptimized: false)
!20 = !DISubroutineType(types: !21)
!21 = !{null, !22}
!22 = !DICompositeType(tag: DW_TAG_structure_type, name: "smallPayload", file: !1, line: 11, size: 192, align: 32, elements: !23)
!23 = !{!24, !25}
!24 = !DIDerivedType(tag: DW_TAG_member, name: "color", scope: !22, file: !1, line: 12, baseType: !4, size: 96, align: 32)
!25 = !DIDerivedType(tag: DW_TAG_member, name: "dir", scope: !22, file: !1, line: 13, baseType: !4, size: 96, align: 32, offset: 96)
!26 = !{i32 2, !"Dwarf Version", i32 4}
!27 = !{i32 2, !"Debug Info Version", i32 3}
!28 = !{!"dxc(private) 1.9.0.5433 (triage, ab5400907)"}
!29 = !{!"repro.hlsl", !"// Repro for microsoft/DirectXShaderCompiler#2923.\0D\0A//\0D\0A// This is PixTest.cpp's PixStructAnnotation_SequentialFloatN shader with the\0D\0A// edit the issue asks for: the payload struct is passed to a subroutine, and\0D\0A// the subroutine calls DispatchMesh.\0D\0A//\0D\0A// The symptom is in the PIX \22numbering\22 pass, so this file has to be run\0D\0A// through -dxil-dbg-value-to-dbg-declare + -dxil-annotate-with-virtual-regs;\0D\0A// see run-2923.cmd.\0D\0A\0D\0Astruct smallPayload {\0D\0A  float3 color;\0D\0A  float3 dir;\0D\0A};\0D\0A\0D\0Avoid Sub(smallPayload p) { DispatchMesh(1, 1, 1, p); }\0D\0A\0D\0A[numthreads(1, 1, 1)] void main() {\0D\0A  smallPayload p;\0D\0A  p.color = float3(1, 2, 3);\0D\0A  p.dir = float3(4, 5, 6);\0D\0A\0D\0A  Sub(p);\0D\0A}\0D\0A"}
!30 = !{!"repro.hlsl"}
!31 = !{!"-E", !"main", !"-T", !"as_6_5", !"-O1", !"-HV", !"2018", !"-enable-16bit-types", !"-Zi", !"-Qembed_debug", !"-Fo", !"repro-O1.dxo"}
!32 = !{i32 1, i32 5}
!33 = !{i32 1, i32 10}
!34 = !{!"as", i32 6, i32 5}
!35 = !{i32 0, %struct.smallPayload.0 undef, !36}
!36 = !{i32 0, !37, !38}
!37 = !{i32 6, !"color", i32 3, i32 0, i32 7, i32 9}
!38 = !{i32 6, !"dir", i32 3, i32 16, i32 7, i32 9}
!39 = !{i32 1, void ()* @main, !40}
!40 = !{!41}
!41 = !{i32 1, !2, !2}
!42 = !{void ()* @main, !"main", null, null, !43}
!43 = !{i32 0, i64 8388608, i32 10, !44}
!44 = !{!45, i32 24}
!45 = !{i32 1, i32 1, i32 1}
!46 = !{i32 1, i32 0, i32 1}
!47 = !DILocalVariable(tag: DW_TAG_arg_variable, name: "p", arg: 1, scope: !19, file: !1, line: 16, type: !22)
!48 = !DIExpression(DW_OP_bit_piece, 0, 32)
!49 = !DILocation(line: 16, column: 23, scope: !19, inlinedAt: !50)
!50 = distinct !DILocation(line: 23, column: 3, scope: !16)
!51 = !DIExpression(DW_OP_bit_piece, 32, 32)
!52 = !{i32 1, i32 2, i32 1}
!53 = !DIExpression(DW_OP_bit_piece, 64, 32)
!54 = !{i32 1, i32 3, i32 1}
!55 = !DIExpression(DW_OP_bit_piece, 96, 32)
!56 = !{i32 1, i32 4, i32 1}
!57 = !DIExpression(DW_OP_bit_piece, 128, 32)
!58 = !{i32 1, i32 5, i32 1}
!59 = !DIExpression(DW_OP_bit_piece, 160, 32)
!60 = !{i32 1, i32 6, i32 1}
!61 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "p", scope: !16, file: !1, line: 19, type: !22)
!62 = !DILocation(line: 19, column: 16, scope: !16)
!63 = !{i32 1, i32 7, i32 1}
!64 = !{i32 1, i32 8, i32 1}
!65 = !{i32 1, i32 9, i32 1}
!66 = !{i32 1, i32 10, i32 1}
!67 = !{i32 1, i32 11, i32 1}
!68 = !{i32 1, i32 12, i32 6}
!69 = !{i32 0, i32 12}
!70 = !{i32 3, i32 0}
!71 = !{i32 3, i32 1}
!72 = !{i32 2, !68, i32 1, i32 0}
!73 = !{i32 3, i32 2}
!74 = !{i32 3, i32 3}
!75 = !{i32 2, !68, i32 1, i32 1}
!76 = !{i32 3, i32 4}
!77 = !{i32 3, i32 5}
!78 = !{i32 2, !68, i32 1, i32 2}
!79 = !{i32 0, i32 15}
!80 = !{i32 3, i32 6}
!81 = !{i32 3, i32 7}
!82 = !{i32 2, !68, i32 1, i32 3}
!83 = !{i32 3, i32 8}
!84 = !{i32 3, i32 9}
!85 = !{i32 2, !68, i32 1, i32 4}
!86 = !{i32 3, i32 10}
!87 = !{i32 3, i32 11}
!88 = !{i32 2, !68, i32 1, i32 5}
!89 = !DILocation(line: 16, column: 28, scope: !19, inlinedAt: !50)
!90 = !{i32 3, i32 12}
!91 = !{i32 3, i32 13}
!92 = !{i32 0, i32 18}
!93 = !{i32 3, i32 14}
!94 = !{i32 0, i32 19}
!95 = !{i32 3, i32 15}
!96 = !{i32 0, i32 20}
!97 = !{i32 3, i32 16}
!98 = !{i32 3, i32 17}
!99 = !{i32 0, i32 21}
!100 = !{i32 3, i32 18}
!101 = !{i32 0, i32 22}
!102 = !{i32 3, i32 19}
!103 = !{i32 0, i32 23}
!104 = !{i32 3, i32 20}
!105 = !{i32 0, i32 0}
!106 = !{i32 3, i32 21}
!107 = !{i32 3, i32 22}
!108 = !{i32 2, !46, i32 1, i32 0}
!109 = !{i32 0, i32 1}
!110 = !{i32 3, i32 23}
!111 = !{i32 3, i32 24}
!112 = !{i32 2, !45, i32 1, i32 0}
!113 = !{i32 0, i32 2}
!114 = !{i32 3, i32 25}
!115 = !{i32 3, i32 26}
!116 = !{i32 2, !52, i32 1, i32 0}
!117 = !{i32 0, i32 3}
!118 = !{i32 3, i32 27}
!119 = !{i32 3, i32 28}
!120 = !{i32 2, !54, i32 1, i32 0}
!121 = !{i32 0, i32 4}
!122 = !{i32 3, i32 29}
!123 = !{i32 3, i32 30}
!124 = !{i32 2, !56, i32 1, i32 0}
!125 = !{i32 0, i32 5}
!126 = !{i32 3, i32 31}
!127 = !{i32 3, i32 32}
!128 = !{i32 2, !58, i32 1, i32 0}
!129 = !{i32 3, i32 33}
!130 = !DILocation(line: 24, column: 1, scope: !16)
!131 = !{i32 3, i32 34}
