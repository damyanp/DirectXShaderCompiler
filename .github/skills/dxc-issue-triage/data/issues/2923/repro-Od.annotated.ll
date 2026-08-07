; ModuleID = 'repro-Od.annotated.bc'
target datalayout = "e-m:e-p:32:32-i1:32-i8:8-i16:16-i32:32-i64:64-f16:16-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%struct.smallPayload.0 = type { [3 x float], [3 x float] }

@dx.nothing.a = internal constant [1 x i32] zeroinitializer

define void @main() {
entry:
  %0 = alloca [1 x float], i32 0, !pix-alloca-reg !46
  call void @llvm.dbg.declare(metadata [1 x float]* %0, metadata !47, metadata !48), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %1 = alloca [1 x float], i32 0, !pix-alloca-reg !45
  call void @llvm.dbg.declare(metadata [1 x float]* %1, metadata !47, metadata !50), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  %2 = alloca [1 x float], i32 0, !pix-alloca-reg !51
  call void @llvm.dbg.declare(metadata [1 x float]* %2, metadata !47, metadata !52), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 64, 32)
  %3 = alloca [1 x float], i32 0, !pix-alloca-reg !53
  call void @llvm.dbg.declare(metadata [1 x float]* %3, metadata !47, metadata !54), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 96, 32)
  %4 = alloca [1 x float], i32 0, !pix-alloca-reg !55
  call void @llvm.dbg.declare(metadata [1 x float]* %4, metadata !47, metadata !56), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 128, 32)
  %5 = alloca [1 x float], i32 0, !pix-alloca-reg !57
  call void @llvm.dbg.declare(metadata [1 x float]* %5, metadata !47, metadata !58), !dbg !49 ; var:"p" !DIExpression(DW_OP_bit_piece, 160, 32)
  %6 = alloca %struct.smallPayload.0, !dbg !59, !pix-alloca-reg !61 ; line:16 col:23
  %7 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !62, !pix-dxil-reg !63, !pix-dxil-inst-num !64 ; line:20 col:11
  %8 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !65, !pix-dxil-reg !66, !pix-dxil-inst-num !67 ; line:21 col:9
  %9 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !68, !pix-dxil-reg !69, !pix-dxil-inst-num !70 ; line:23 col:3
  %10 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %6, i32 0, i32 0, i32 0, !dbg !59, !pix-dxil-reg !71, !pix-dxil-inst-num !72 ; line:16 col:23
  store float 1.000000e+00, float* %10, !dbg !59, !pix-dxil-inst-num !73, !pix-alloca-reg-write !74 ; line:16 col:23
  %11 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %6, i32 0, i32 0, i32 1, !dbg !59, !pix-dxil-reg !71, !pix-dxil-inst-num !75 ; line:16 col:23
  store float 2.000000e+00, float* %11, !dbg !59, !pix-dxil-inst-num !76, !pix-alloca-reg-write !77 ; line:16 col:23
  %12 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %6, i32 0, i32 0, i32 2, !dbg !59, !pix-dxil-reg !71, !pix-dxil-inst-num !78 ; line:16 col:23
  store float 3.000000e+00, float* %12, !dbg !59, !pix-dxil-inst-num !79, !pix-alloca-reg-write !80 ; line:16 col:23
  %13 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %6, i32 0, i32 1, i32 0, !dbg !59, !pix-dxil-reg !81, !pix-dxil-inst-num !82 ; line:16 col:23
  store float 4.000000e+00, float* %13, !dbg !59, !pix-dxil-inst-num !83, !pix-alloca-reg-write !84 ; line:16 col:23
  %14 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %6, i32 0, i32 1, i32 1, !dbg !59, !pix-dxil-reg !81, !pix-dxil-inst-num !85 ; line:16 col:23
  store float 5.000000e+00, float* %14, !dbg !59, !pix-dxil-inst-num !86, !pix-alloca-reg-write !87 ; line:16 col:23
  %15 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %6, i32 0, i32 1, i32 2, !dbg !59, !pix-dxil-reg !81, !pix-dxil-inst-num !88 ; line:16 col:23
  store float 6.000000e+00, float* %15, !dbg !59, !pix-dxil-inst-num !89, !pix-alloca-reg-write !90 ; line:16 col:23
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* %6), !dbg !91, !pix-dxil-inst-num !92 ; line:16 col:28
  %16 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !93, !pix-dxil-reg !94, !pix-dxil-inst-num !95 ; line:16 col:54
  %17 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !96, !pix-dxil-reg !97, !pix-dxil-inst-num !98 ; line:24 col:1
  call void @llvm.dbg.declare(metadata %struct.smallPayload.0* %6, metadata !99, metadata !100), !dbg !59 ; var:"p" !DIExpression()
  ret void, !dbg !96, !pix-dxil-inst-num !101 ; line:24 col:1
}

; Function Attrs: nounwind readnone
declare void @llvm.dbg.declare(metadata, metadata, metadata) #0

; Function Attrs: nounwind readnone
declare void @llvm.dbg.value(metadata, i64, metadata, metadata) #0

; Function Attrs: nounwind
declare void @dx.op.dispatchMesh.struct.smallPayload.0(i32, i32, i32, i32, %struct.smallPayload.0*) #1

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
!31 = !{!"-E", !"main", !"-T", !"as_6_5", !"-Od", !"-HV", !"2018", !"-enable-16bit-types", !"-Zi", !"-Qembed_debug", !"-Fo", !"repro-Od.dxo"}
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
!43 = !{i32 0, i64 8388609, i32 10, !44}
!44 = !{!45, i32 24}
!45 = !{i32 1, i32 1, i32 1}
!46 = !{i32 1, i32 0, i32 1}
!47 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "p", scope: !16, file: !1, line: 19, type: !22)
!48 = !DIExpression(DW_OP_bit_piece, 0, 32)
!49 = !DILocation(line: 19, column: 16, scope: !16)
!50 = !DIExpression(DW_OP_bit_piece, 32, 32)
!51 = !{i32 1, i32 2, i32 1}
!52 = !DIExpression(DW_OP_bit_piece, 64, 32)
!53 = !{i32 1, i32 3, i32 1}
!54 = !DIExpression(DW_OP_bit_piece, 96, 32)
!55 = !{i32 1, i32 4, i32 1}
!56 = !DIExpression(DW_OP_bit_piece, 128, 32)
!57 = !{i32 1, i32 5, i32 1}
!58 = !DIExpression(DW_OP_bit_piece, 160, 32)
!59 = !DILocation(line: 16, column: 23, scope: !19, inlinedAt: !60)
!60 = distinct !DILocation(line: 23, column: 3, scope: !16)
!61 = !{i32 1, i32 6, i32 6}
!62 = !DILocation(line: 20, column: 11, scope: !16)
!63 = !{i32 0, i32 12}
!64 = !{i32 3, i32 0}
!65 = !DILocation(line: 21, column: 9, scope: !16)
!66 = !{i32 0, i32 13}
!67 = !{i32 3, i32 1}
!68 = !DILocation(line: 23, column: 3, scope: !16)
!69 = !{i32 0, i32 14}
!70 = !{i32 3, i32 2}
!71 = !{i32 0, i32 6}
!72 = !{i32 3, i32 3}
!73 = !{i32 3, i32 4}
!74 = !{i32 2, !61, i32 1, i32 0}
!75 = !{i32 3, i32 5}
!76 = !{i32 3, i32 6}
!77 = !{i32 2, !61, i32 1, i32 1}
!78 = !{i32 3, i32 7}
!79 = !{i32 3, i32 8}
!80 = !{i32 2, !61, i32 1, i32 2}
!81 = !{i32 0, i32 9}
!82 = !{i32 3, i32 9}
!83 = !{i32 3, i32 10}
!84 = !{i32 2, !61, i32 1, i32 3}
!85 = !{i32 3, i32 11}
!86 = !{i32 3, i32 12}
!87 = !{i32 2, !61, i32 1, i32 4}
!88 = !{i32 3, i32 13}
!89 = !{i32 3, i32 14}
!90 = !{i32 2, !61, i32 1, i32 5}
!91 = !DILocation(line: 16, column: 28, scope: !19, inlinedAt: !60)
!92 = !{i32 3, i32 15}
!93 = !DILocation(line: 16, column: 54, scope: !19, inlinedAt: !60)
!94 = !{i32 0, i32 15}
!95 = !{i32 3, i32 16}
!96 = !DILocation(line: 24, column: 1, scope: !16)
!97 = !{i32 0, i32 16}
!98 = !{i32 3, i32 17}
!99 = !DILocalVariable(tag: DW_TAG_arg_variable, name: "p", arg: 1, scope: !19, file: !1, line: 16, type: !22)
!100 = !DIExpression()
!101 = !{i32 3, i32 18}
