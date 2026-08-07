; ModuleID = 'control-inout-param-Od.annotated.bc'
target datalayout = "e-m:e-p:32:32-i1:32-i8:8-i16:16-i32:32-i64:64-f16:16-f32:32-f64:64-n8:16:32:64"
target triple = "dxil-ms-dx"

%struct.smallPayload.0 = type { [3 x float], [3 x float] }

@dx.nothing.a = internal constant [1 x i32] zeroinitializer

define void @main() {
entry:
  %p1 = alloca %struct.smallPayload.0, !pix-alloca-reg !47
  call void @llvm.dbg.declare(metadata %struct.smallPayload.0* %p1, metadata !48, metadata !49), !dbg !50 ; var:"p" !DIExpression()
  %0 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !51, !pix-dxil-reg !52, !pix-dxil-inst-num !53 ; line:18 col:11
  %1 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 0, !dbg !51, !pix-dxil-reg !54, !pix-dxil-inst-num !55 ; line:18 col:11
  store float 1.000000e+00, float* %1, !dbg !51, !pix-dxil-inst-num !56, !pix-alloca-reg-write !57 ; line:18 col:11
  %2 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 1, !dbg !51, !pix-dxil-reg !54, !pix-dxil-inst-num !58 ; line:18 col:11
  store float 2.000000e+00, float* %2, !dbg !51, !pix-dxil-inst-num !59, !pix-alloca-reg-write !60 ; line:18 col:11
  %3 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 0, i32 2, !dbg !51, !pix-dxil-reg !54, !pix-dxil-inst-num !61 ; line:18 col:11
  store float 3.000000e+00, float* %3, !dbg !51, !pix-dxil-inst-num !62, !pix-alloca-reg-write !63 ; line:18 col:11
  %4 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !64, !pix-dxil-reg !65, !pix-dxil-inst-num !66 ; line:19 col:9
  %5 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 0, !dbg !64, !pix-dxil-reg !67, !pix-dxil-inst-num !68 ; line:19 col:9
  store float 4.000000e+00, float* %5, !dbg !64, !pix-dxil-inst-num !69, !pix-alloca-reg-write !70 ; line:19 col:9
  %6 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 1, !dbg !64, !pix-dxil-reg !67, !pix-dxil-inst-num !71 ; line:19 col:9
  store float 5.000000e+00, float* %6, !dbg !64, !pix-dxil-inst-num !72, !pix-alloca-reg-write !73 ; line:19 col:9
  %7 = getelementptr inbounds %struct.smallPayload.0, %struct.smallPayload.0* %p1, i32 0, i32 1, i32 2, !dbg !64, !pix-dxil-reg !67, !pix-dxil-inst-num !74 ; line:19 col:9
  store float 6.000000e+00, float* %7, !dbg !64, !pix-dxil-inst-num !75, !pix-alloca-reg-write !76 ; line:19 col:9
  %8 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !77, !pix-dxil-reg !78, !pix-dxil-inst-num !79 ; line:21 col:3
  call void @llvm.dbg.declare(metadata %struct.smallPayload.0* %p1, metadata !80, metadata !49) #1, !dbg !81 ; var:"p" !DIExpression()
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* %p1), !dbg !83, !pix-dxil-inst-num !84 ; line:14 col:34
  %9 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !85, !pix-dxil-reg !86, !pix-dxil-inst-num !87 ; line:14 col:60
  %10 = load i32, i32* getelementptr inbounds ([1 x i32], [1 x i32]* @dx.nothing.a, i32 0, i32 0), !dbg !88, !pix-dxil-reg !89, !pix-dxil-inst-num !90 ; line:22 col:1
  ret void, !dbg !88, !pix-dxil-inst-num !91 ; line:22 col:1
}

; Function Attrs: nounwind readnone
declare void @llvm.dbg.declare(metadata, metadata, metadata) #0

; Function Attrs: nounwind
declare void @dx.op.dispatchMesh.struct.smallPayload.0(i32, i32, i32, i32, %struct.smallPayload.0*) #1

attributes #0 = { nounwind readnone }
attributes #1 = { nounwind }

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
!32 = !{!"-E", !"main", !"-T", !"as_6_5", !"-Od", !"-HV", !"2018", !"-enable-16bit-types", !"-Zi", !"-Qembed_debug", !"-Fo", !"control-inout-param-Od.dxo"}
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
!44 = !{i32 0, i64 8388609, i32 10, !45}
!45 = !{!46, i32 24}
!46 = !{i32 1, i32 1, i32 1}
!47 = !{i32 1, i32 0, i32 6}
!48 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "p", scope: !16, file: !1, line: 17, type: !23)
!49 = !DIExpression()
!50 = !DILocation(line: 17, column: 16, scope: !16)
!51 = !DILocation(line: 18, column: 11, scope: !16)
!52 = !{i32 0, i32 6}
!53 = !{i32 3, i32 0}
!54 = !{i32 0, i32 0}
!55 = !{i32 3, i32 1}
!56 = !{i32 3, i32 2}
!57 = !{i32 2, !47, i32 1, i32 0}
!58 = !{i32 3, i32 3}
!59 = !{i32 3, i32 4}
!60 = !{i32 2, !47, i32 1, i32 1}
!61 = !{i32 3, i32 5}
!62 = !{i32 3, i32 6}
!63 = !{i32 2, !47, i32 1, i32 2}
!64 = !DILocation(line: 19, column: 9, scope: !16)
!65 = !{i32 0, i32 7}
!66 = !{i32 3, i32 7}
!67 = !{i32 0, i32 3}
!68 = !{i32 3, i32 8}
!69 = !{i32 3, i32 9}
!70 = !{i32 2, !47, i32 1, i32 3}
!71 = !{i32 3, i32 10}
!72 = !{i32 3, i32 11}
!73 = !{i32 2, !47, i32 1, i32 4}
!74 = !{i32 3, i32 12}
!75 = !{i32 3, i32 13}
!76 = !{i32 2, !47, i32 1, i32 5}
!77 = !DILocation(line: 21, column: 3, scope: !16)
!78 = !{i32 0, i32 8}
!79 = !{i32 3, i32 14}
!80 = !DILocalVariable(tag: DW_TAG_arg_variable, name: "p", arg: 1, scope: !19, file: !1, line: 14, type: !23)
!81 = !DILocation(line: 14, column: 29, scope: !19, inlinedAt: !82)
!82 = distinct !DILocation(line: 21, column: 3, scope: !16)
!83 = !DILocation(line: 14, column: 34, scope: !19, inlinedAt: !82)
!84 = !{i32 3, i32 15}
!85 = !DILocation(line: 14, column: 60, scope: !19, inlinedAt: !82)
!86 = !{i32 0, i32 9}
!87 = !{i32 3, i32 16}
!88 = !DILocation(line: 22, column: 1, scope: !16)
!89 = !{i32 0, i32 10}
!90 = !{i32 3, i32 17}
!91 = !{i32 3, i32 18}
