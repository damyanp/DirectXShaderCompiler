; ModuleID = 'control-inout-param-O1.annotated.bc'
target datalayout = "e-m:e-p:32:32-i1:32-i8:8-i16:16-i32:32-i64:64-f16:16-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%struct.smallPayload.0 = type { [3 x float], [3 x float] }

define void @main() {
entry:
  %0 = alloca [1 x float], i32 0, !pix-alloca-reg !47
  call void @llvm.dbg.declare(metadata [1 x float]* %0, metadata !48, metadata !49), !dbg !50 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %1 = alloca [1 x float], i32 0, !pix-alloca-reg !46
  call void @llvm.dbg.declare(metadata [1 x float]* %1, metadata !48, metadata !52), !dbg !50 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  %2 = alloca [1 x float], i32 0, !pix-alloca-reg !53
  call void @llvm.dbg.declare(metadata [1 x float]* %2, metadata !48, metadata !54), !dbg !50 ; var:"p" !DIExpression(DW_OP_bit_piece, 64, 32)
  %3 = alloca [1 x float], i32 0, !pix-alloca-reg !55
  call void @llvm.dbg.declare(metadata [1 x float]* %3, metadata !48, metadata !56), !dbg !50 ; var:"p" !DIExpression(DW_OP_bit_piece, 96, 32)
  %4 = alloca [1 x float], i32 0, !pix-alloca-reg !57
  call void @llvm.dbg.declare(metadata [1 x float]* %4, metadata !48, metadata !58), !dbg !50 ; var:"p" !DIExpression(DW_OP_bit_piece, 128, 32)
  %5 = alloca [1 x float], i32 0, !pix-alloca-reg !59
  call void @llvm.dbg.declare(metadata [1 x float]* %5, metadata !48, metadata !60), !dbg !50 ; var:"p" !DIExpression(DW_OP_bit_piece, 160, 32)
  %6 = alloca [1 x float], i32 0, !pix-alloca-reg !61
  call void @llvm.dbg.declare(metadata [1 x float]* %6, metadata !62, metadata !49), !dbg !63 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %7 = alloca [1 x float], i32 0, !pix-alloca-reg !64
  call void @llvm.dbg.declare(metadata [1 x float]* %7, metadata !62, metadata !52), !dbg !63 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  %8 = alloca [1 x float], i32 0, !pix-alloca-reg !65
  call void @llvm.dbg.declare(metadata [1 x float]* %8, metadata !62, metadata !54), !dbg !63 ; var:"p" !DIExpression(DW_OP_bit_piece, 64, 32)
  %9 = alloca [1 x float], i32 0, !pix-alloca-reg !66
  call void @llvm.dbg.declare(metadata [1 x float]* %9, metadata !62, metadata !56), !dbg !63 ; var:"p" !DIExpression(DW_OP_bit_piece, 96, 32)
  %10 = alloca [1 x float], i32 0, !pix-alloca-reg !67
  call void @llvm.dbg.declare(metadata [1 x float]* %10, metadata !62, metadata !58), !dbg !63 ; var:"p" !DIExpression(DW_OP_bit_piece, 128, 32)
  %11 = alloca [1 x float], i32 0, !pix-alloca-reg !68
  call void @llvm.dbg.declare(metadata [1 x float]* %11, metadata !62, metadata !60), !dbg !63 ; var:"p" !DIExpression(DW_OP_bit_piece, 160, 32)
  %p1 = alloca %struct.smallPayload.0, align 8, !pix-alloca-reg !69
  %12 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 0, !dbg !70, !pix-dxil-reg !71, !pix-dxil-inst-num !72 ; line:18 col:11
  store float 1.000000e+00, float* %12, align 8, !dbg !70, !pix-dxil-inst-num !73, !pix-alloca-reg-write !74 ; line:18 col:11
  %13 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 1, !dbg !70, !pix-dxil-reg !71, !pix-dxil-inst-num !75 ; line:18 col:11
  store float 2.000000e+00, float* %13, align 4, !dbg !70, !pix-dxil-inst-num !76, !pix-alloca-reg-write !77 ; line:18 col:11
  %14 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 2, !dbg !70, !pix-dxil-reg !71, !pix-dxil-inst-num !78 ; line:18 col:11
  store float 3.000000e+00, float* %14, align 8, !dbg !70, !pix-dxil-inst-num !79, !pix-alloca-reg-write !80 ; line:18 col:11
  %15 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 0, !dbg !81, !pix-dxil-reg !82, !pix-dxil-inst-num !83 ; line:19 col:9
  store float 4.000000e+00, float* %15, align 4, !dbg !81, !pix-dxil-inst-num !84, !pix-alloca-reg-write !85 ; line:19 col:9
  %16 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 1, !dbg !81, !pix-dxil-reg !82, !pix-dxil-inst-num !86 ; line:19 col:9
  store float 5.000000e+00, float* %16, align 4, !dbg !81, !pix-dxil-inst-num !87, !pix-alloca-reg-write !88 ; line:19 col:9
  %17 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 2, !dbg !81, !pix-dxil-reg !82, !pix-dxil-inst-num !89 ; line:19 col:9
  store float 6.000000e+00, float* %17, align 4, !dbg !81, !pix-dxil-inst-num !90, !pix-alloca-reg-write !91 ; line:19 col:9
  %18 = load %struct.smallPayload.0, %struct.smallPayload.0* %p1, !dbg !50, !pix-dxil-inst-num !92 ; line:14 col:29
  %19 = extractvalue %struct.smallPayload.0 %18, 0, !pix-dxil-inst-num !93
  %20 = extractvalue [3 x float] %19, 0, !pix-dxil-reg !94, !pix-dxil-inst-num !95
  %21 = extractvalue [3 x float] %19, 1, !pix-dxil-reg !96, !pix-dxil-inst-num !97
  %22 = extractvalue [3 x float] %19, 2, !pix-dxil-reg !98, !pix-dxil-inst-num !99
  %23 = extractvalue %struct.smallPayload.0 %18, 1, !pix-dxil-inst-num !100
  %24 = extractvalue [3 x float] %23, 0, !pix-dxil-reg !101, !pix-dxil-inst-num !102
  %25 = extractvalue [3 x float] %23, 1, !pix-dxil-reg !103, !pix-dxil-inst-num !104
  %26 = extractvalue [3 x float] %23, 2, !pix-dxil-reg !105, !pix-dxil-inst-num !106
  %27 = getelementptr [1 x float], [1 x float]* %6, i32 0, i32 0, !pix-dxil-reg !107, !pix-dxil-inst-num !108
  store float %20, float* %27, !pix-dxil-inst-num !109, !pix-alloca-reg-write !110
  %28 = getelementptr [1 x float], [1 x float]* %7, i32 0, i32 0, !pix-dxil-reg !111, !pix-dxil-inst-num !112
  store float %21, float* %28, !pix-dxil-inst-num !113, !pix-alloca-reg-write !114
  %29 = getelementptr [1 x float], [1 x float]* %8, i32 0, i32 0, !pix-dxil-reg !115, !pix-dxil-inst-num !116
  store float %22, float* %29, !pix-dxil-inst-num !117, !pix-alloca-reg-write !118
  %30 = getelementptr [1 x float], [1 x float]* %9, i32 0, i32 0, !pix-dxil-reg !119, !pix-dxil-inst-num !120
  store float %24, float* %30, !pix-dxil-inst-num !121, !pix-alloca-reg-write !122
  %31 = getelementptr [1 x float], [1 x float]* %10, i32 0, i32 0, !pix-dxil-reg !123, !pix-dxil-inst-num !124
  store float %25, float* %31, !pix-dxil-inst-num !125, !pix-alloca-reg-write !126
  %32 = getelementptr [1 x float], [1 x float]* %11, i32 0, i32 0, !pix-dxil-reg !127, !pix-dxil-inst-num !128
  store float %26, float* %32, !pix-dxil-inst-num !129, !pix-alloca-reg-write !130
  %33 = load %struct.smallPayload.0, %struct.smallPayload.0* %p1, !dbg !131, !pix-dxil-inst-num !132 ; line:14 col:34
  %34 = extractvalue %struct.smallPayload.0 %33, 0, !pix-dxil-inst-num !133
  %35 = extractvalue [3 x float] %34, 0, !pix-dxil-reg !134, !pix-dxil-inst-num !135
  %36 = extractvalue [3 x float] %34, 1, !pix-dxil-reg !136, !pix-dxil-inst-num !137
  %37 = extractvalue [3 x float] %34, 2, !pix-dxil-reg !138, !pix-dxil-inst-num !139
  %38 = extractvalue %struct.smallPayload.0 %33, 1, !pix-dxil-inst-num !140
  %39 = extractvalue [3 x float] %38, 0, !pix-dxil-reg !141, !pix-dxil-inst-num !142
  %40 = extractvalue [3 x float] %38, 1, !pix-dxil-reg !143, !pix-dxil-inst-num !144
  %41 = extractvalue [3 x float] %38, 2, !pix-dxil-reg !145, !pix-dxil-inst-num !146
  %42 = getelementptr [1 x float], [1 x float]* %0, i32 0, i32 0, !pix-dxil-reg !147, !pix-dxil-inst-num !148
  store float %35, float* %42, !pix-dxil-inst-num !149, !pix-alloca-reg-write !150
  %43 = getelementptr [1 x float], [1 x float]* %1, i32 0, i32 0, !pix-dxil-reg !151, !pix-dxil-inst-num !152
  store float %36, float* %43, !pix-dxil-inst-num !153, !pix-alloca-reg-write !154
  %44 = getelementptr [1 x float], [1 x float]* %2, i32 0, i32 0, !pix-dxil-reg !155, !pix-dxil-inst-num !156
  store float %37, float* %44, !pix-dxil-inst-num !157, !pix-alloca-reg-write !158
  %45 = getelementptr [1 x float], [1 x float]* %3, i32 0, i32 0, !pix-dxil-reg !159, !pix-dxil-inst-num !160
  store float %39, float* %45, !pix-dxil-inst-num !161, !pix-alloca-reg-write !162
  %46 = getelementptr [1 x float], [1 x float]* %4, i32 0, i32 0, !pix-dxil-reg !163, !pix-dxil-inst-num !164
  store float %40, float* %46, !pix-dxil-inst-num !165, !pix-alloca-reg-write !166
  %47 = getelementptr [1 x float], [1 x float]* %5, i32 0, i32 0, !pix-dxil-reg !167, !pix-dxil-inst-num !168
  store float %41, float* %47, !pix-dxil-inst-num !169, !pix-alloca-reg-write !170
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* nonnull %p1), !dbg !131, !pix-dxil-inst-num !171 ; line:14 col:34
  ret void, !dbg !172, !pix-dxil-inst-num !173 ; line:22 col:1
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
!llvm.module.flags = !{!27, !28}
!llvm.ident = !{!29}
!dx.source.contents = !{!30}
!dx.source.defines = !{!2}
!dx.source.mainFileName = !{!31}
!dx.source.args = !{!32}
!dx.version = !{!33}
!dx.valver = !{!34}
!dx.shaderModel = !{!35}
!dx.typeAnnotations = !{!36, !40}
!dx.entryPoints = !{!43}

!0 = distinct !DICompileUnit(language: DW_LANG_C_plus_plus, file: !1, producer: "dxc(private) 1.9.0.5433 (triage, ab5400907)", isOptimized: false, runtimeVersion: 0, emissionKind: 1, enums: !2, retainedTypes: !3, subprograms: !15)
!1 = !DIFile(filename: "control-inout-param.hlsl", directory: "")
!2 = !{}
!3 = !{!4}
!4 = !DIDerivedType(tag: DW_TAG_typedef, name: "float3", file: !1, line: 17, baseType: !5)
!5 = !DICompositeType(tag: DW_TAG_class_type, name: "vector<float, 3>", file: !1, line: 17, size: 96, align: 32, elements: !6, templateParams: !11)
!6 = !{!7, !9, !10}
!7 = !DIDerivedType(tag: DW_TAG_member, name: "x", scope: !5, file: !1, line: 17, baseType: !8, size: 32, align: 32, flags: DIFlagPublic)
!8 = !DIBasicType(name: "float", size: 32, align: 32, encoding: DW_ATE_float)
!9 = !DIDerivedType(tag: DW_TAG_member, name: "y", scope: !5, file: !1, line: 17, baseType: !8, size: 32, align: 32, offset: 32, flags: DIFlagPublic)
!10 = !DIDerivedType(tag: DW_TAG_member, name: "z", scope: !5, file: !1, line: 17, baseType: !8, size: 32, align: 32, offset: 64, flags: DIFlagPublic)
!11 = !{!12, !13}
!12 = !DITemplateTypeParameter(name: "element", type: !8)
!13 = !DITemplateValueParameter(name: "element_count", type: !14, value: i32 3)
!14 = !DIBasicType(name: "int", size: 32, align: 32, encoding: DW_ATE_signed)
!15 = !{!16, !19}
!16 = !DISubprogram(name: "main", scope: !1, file: !1, line: 16, type: !17, isLocal: false, isDefinition: true, scopeLine: 16, flags: DIFlagPrototyped, isOptimized: false, function: void ()* @main)
!17 = !DISubroutineType(types: !18)
!18 = !{null}
!19 = !DISubprogram(name: "Sub", linkageName: "\01?Sub@@YAXUsmallPayload@@@Z", scope: !1, file: !1, line: 14, type: !20, isLocal: false, isDefinition: true, scopeLine: 14, flags: DIFlagPrototyped, isOptimized: false)
!20 = !DISubroutineType(types: !21)
!21 = !{null, !22}
!22 = !DIDerivedType(tag: DW_TAG_restrict_type, baseType: !23)
!23 = !DICompositeType(tag: DW_TAG_structure_type, name: "smallPayload", file: !1, line: 9, size: 192, align: 32, elements: !24)
!24 = !{!25, !26}
!25 = !DIDerivedType(tag: DW_TAG_member, name: "color", scope: !23, file: !1, line: 10, baseType: !4, size: 96, align: 32)
!26 = !DIDerivedType(tag: DW_TAG_member, name: "dir", scope: !23, file: !1, line: 11, baseType: !4, size: 96, align: 32, offset: 96)
!27 = !{i32 2, !"Dwarf Version", i32 4}
!28 = !{i32 2, !"Debug Info Version", i32 3}
!29 = !{!"dxc(private) 1.9.0.5433 (triage, ab5400907)"}
!30 = !{!"control-inout-param.hlsl", !"// Second control for microsoft/DirectXShaderCompiler#2923.\0D\0A//\0D\0A// repro.hlsl with ONE token changed: the subroutine takes the payload by\0D\0A// `inout` instead of by value, so no copy of the struct is made. Everything\0D\0A// else -- the struct, the writes in main, the subroutine, the DispatchMesh\0D\0A// inside the subroutine -- is identical. It isolates the by-value copy as the\0D\0A// trigger rather than \22calling a subroutine at all\22.\0D\0A\0D\0Astruct smallPayload {\0D\0A  float3 color;\0D\0A  float3 dir;\0D\0A};\0D\0A\0D\0Avoid Sub(inout smallPayload p) { DispatchMesh(1, 1, 1, p); }\0D\0A\0D\0A[numthreads(1, 1, 1)] void main() {\0D\0A  smallPayload p;\0D\0A  p.color = float3(1, 2, 3);\0D\0A  p.dir = float3(4, 5, 6);\0D\0A\0D\0A  Sub(p);\0D\0A}\0D\0A"}
!31 = !{!"control-inout-param.hlsl"}
!32 = !{!"-E", !"main", !"-T", !"as_6_5", !"-O1", !"-HV", !"2018", !"-enable-16bit-types", !"-Zi", !"-Qembed_debug", !"-Fo", !"control-inout-param-O1.dxo"}
!33 = !{i32 1, i32 5}
!34 = !{i32 1, i32 10}
!35 = !{!"as", i32 6, i32 5}
!36 = !{i32 0, %struct.smallPayload.0 undef, !37}
!37 = !{i32 0, !38, !39}
!38 = !{i32 6, !"color", i32 3, i32 0, i32 7, i32 9}
!39 = !{i32 6, !"dir", i32 3, i32 16, i32 7, i32 9}
!40 = !{i32 1, void ()* @main, !41}
!41 = !{!42}
!42 = !{i32 1, !2, !2}
!43 = !{void ()* @main, !"main", null, null, !44}
!44 = !{i32 0, i64 8388608, i32 10, !45}
!45 = !{!46, i32 24}
!46 = !{i32 1, i32 1, i32 1}
!47 = !{i32 1, i32 0, i32 1}
!48 = !DILocalVariable(tag: DW_TAG_arg_variable, name: "p", arg: 1, scope: !19, file: !1, line: 14, type: !23)
!49 = !DIExpression(DW_OP_bit_piece, 0, 32)
!50 = !DILocation(line: 14, column: 29, scope: !19, inlinedAt: !51)
!51 = distinct !DILocation(line: 21, column: 3, scope: !16)
!52 = !DIExpression(DW_OP_bit_piece, 32, 32)
!53 = !{i32 1, i32 2, i32 1}
!54 = !DIExpression(DW_OP_bit_piece, 64, 32)
!55 = !{i32 1, i32 3, i32 1}
!56 = !DIExpression(DW_OP_bit_piece, 96, 32)
!57 = !{i32 1, i32 4, i32 1}
!58 = !DIExpression(DW_OP_bit_piece, 128, 32)
!59 = !{i32 1, i32 5, i32 1}
!60 = !DIExpression(DW_OP_bit_piece, 160, 32)
!61 = !{i32 1, i32 6, i32 1}
!62 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "p", scope: !16, file: !1, line: 17, type: !23)
!63 = !DILocation(line: 17, column: 16, scope: !16)
!64 = !{i32 1, i32 7, i32 1}
!65 = !{i32 1, i32 8, i32 1}
!66 = !{i32 1, i32 9, i32 1}
!67 = !{i32 1, i32 10, i32 1}
!68 = !{i32 1, i32 11, i32 1}
!69 = !{i32 1, i32 12, i32 6}
!70 = !DILocation(line: 18, column: 11, scope: !16)
!71 = !{i32 0, i32 12}
!72 = !{i32 3, i32 0}
!73 = !{i32 3, i32 1}
!74 = !{i32 2, !69, i32 1, i32 0}
!75 = !{i32 3, i32 2}
!76 = !{i32 3, i32 3}
!77 = !{i32 2, !69, i32 1, i32 1}
!78 = !{i32 3, i32 4}
!79 = !{i32 3, i32 5}
!80 = !{i32 2, !69, i32 1, i32 2}
!81 = !DILocation(line: 19, column: 9, scope: !16)
!82 = !{i32 0, i32 15}
!83 = !{i32 3, i32 6}
!84 = !{i32 3, i32 7}
!85 = !{i32 2, !69, i32 1, i32 3}
!86 = !{i32 3, i32 8}
!87 = !{i32 3, i32 9}
!88 = !{i32 2, !69, i32 1, i32 4}
!89 = !{i32 3, i32 10}
!90 = !{i32 3, i32 11}
!91 = !{i32 2, !69, i32 1, i32 5}
!92 = !{i32 3, i32 12}
!93 = !{i32 3, i32 13}
!94 = !{i32 0, i32 18}
!95 = !{i32 3, i32 14}
!96 = !{i32 0, i32 19}
!97 = !{i32 3, i32 15}
!98 = !{i32 0, i32 20}
!99 = !{i32 3, i32 16}
!100 = !{i32 3, i32 17}
!101 = !{i32 0, i32 21}
!102 = !{i32 3, i32 18}
!103 = !{i32 0, i32 22}
!104 = !{i32 3, i32 19}
!105 = !{i32 0, i32 23}
!106 = !{i32 3, i32 20}
!107 = !{i32 0, i32 6}
!108 = !{i32 3, i32 21}
!109 = !{i32 3, i32 22}
!110 = !{i32 2, !61, i32 1, i32 0}
!111 = !{i32 0, i32 7}
!112 = !{i32 3, i32 23}
!113 = !{i32 3, i32 24}
!114 = !{i32 2, !64, i32 1, i32 0}
!115 = !{i32 0, i32 8}
!116 = !{i32 3, i32 25}
!117 = !{i32 3, i32 26}
!118 = !{i32 2, !65, i32 1, i32 0}
!119 = !{i32 0, i32 9}
!120 = !{i32 3, i32 27}
!121 = !{i32 3, i32 28}
!122 = !{i32 2, !66, i32 1, i32 0}
!123 = !{i32 0, i32 10}
!124 = !{i32 3, i32 29}
!125 = !{i32 3, i32 30}
!126 = !{i32 2, !67, i32 1, i32 0}
!127 = !{i32 0, i32 11}
!128 = !{i32 3, i32 31}
!129 = !{i32 3, i32 32}
!130 = !{i32 2, !68, i32 1, i32 0}
!131 = !DILocation(line: 14, column: 34, scope: !19, inlinedAt: !51)
!132 = !{i32 3, i32 33}
!133 = !{i32 3, i32 34}
!134 = !{i32 0, i32 24}
!135 = !{i32 3, i32 35}
!136 = !{i32 0, i32 25}
!137 = !{i32 3, i32 36}
!138 = !{i32 0, i32 26}
!139 = !{i32 3, i32 37}
!140 = !{i32 3, i32 38}
!141 = !{i32 0, i32 27}
!142 = !{i32 3, i32 39}
!143 = !{i32 0, i32 28}
!144 = !{i32 3, i32 40}
!145 = !{i32 0, i32 29}
!146 = !{i32 3, i32 41}
!147 = !{i32 0, i32 0}
!148 = !{i32 3, i32 42}
!149 = !{i32 3, i32 43}
!150 = !{i32 2, !47, i32 1, i32 0}
!151 = !{i32 0, i32 1}
!152 = !{i32 3, i32 44}
!153 = !{i32 3, i32 45}
!154 = !{i32 2, !46, i32 1, i32 0}
!155 = !{i32 0, i32 2}
!156 = !{i32 3, i32 46}
!157 = !{i32 3, i32 47}
!158 = !{i32 2, !53, i32 1, i32 0}
!159 = !{i32 0, i32 3}
!160 = !{i32 3, i32 48}
!161 = !{i32 3, i32 49}
!162 = !{i32 2, !55, i32 1, i32 0}
!163 = !{i32 0, i32 4}
!164 = !{i32 3, i32 50}
!165 = !{i32 3, i32 51}
!166 = !{i32 2, !57, i32 1, i32 0}
!167 = !{i32 0, i32 5}
!168 = !{i32 3, i32 52}
!169 = !{i32 3, i32 53}
!170 = !{i32 2, !59, i32 1, i32 0}
!171 = !{i32 3, i32 54}
!172 = !DILocation(line: 22, column: 1, scope: !16)
!173 = !{i32 3, i32 55}
