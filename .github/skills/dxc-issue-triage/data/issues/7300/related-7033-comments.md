## 12/15/2024 10:07:39 @devshgraphicsprogramming

@keptsecret we usually compile with `-fspv-debug=vulkan-with-source` by default, why doesn't our ray query unit test crash as well?

We do have a significant difference that  `lib_6_x` target never worked for us much and we use `cs_`

@ChristianReinbold curious question, why are you using ray-queries and RT pipeline at the same time?

## 12/16/2024 09:42:15 @ChristianReinbold

@devshgraphicsprogramming I always build my MWEs from a small snippet which used to be for the RT pipeline. I never updated the decorator and arguments though. When changing to compute shaders the problem still persists: https://godbolt.org/z/36PMMznKd

Did you double-check that you compile the unit test with the flag? I did not found a configuration nor any hint in the DXC code why ray queries could work with it.

## 12/16/2024 10:38:55 @devshgraphicsprogramming

Now we always tend to use Spir-V intrinsics because there's less problem/hassle for us than relying on the HLSL Spir-V codegen for certain "extensions"

Here's our custom Godbolt and STL library, it works and compiles
https://tinyurl.com/44fk3av7

You can clearly see
```
OpModuleProcessed "dxc-cl-option:  -T cs_6_7 -E main -spirv -Zpr -enable-16bit-types -fvk-use-scalar-layout -Wno-c++11-extensions -Wno-c++1z-extensions -Wno-c++14-extensions -Wno-gnu-static-float-init -fspv-target-env=vulkan1.3 -HV 202x -fspv-debug=source -fspv-debug=tool"
```

@keptsecret can you dig up the version that used HLSL intrinsic style RayQuery ?

## 12/16/2024 10:40:16 @devshgraphicsprogramming

@ChristianReinbold, huh `-fspv-debug=vulkan-with-source` segfaults, but `-fspv-debug=source -fspv-debug=tool` works... hmmm

## 12/16/2024 10:49:37 @devshgraphicsprogramming

OK, there's another similar issue https://github.com/microsoft/DirectXShaderCompiler/issues/5113

The Non-Semantic Debug info extension was authored by the Renderdoc author, Renderdoc probably doesn't support ray-queries yet and definitely doesn't support RT pipeline shaders.

Because of the above, anything that renderdoc doesn't support/won't debug DXC probably never tested emitting `vulkan-with-source` debug info for, and even if it doesn't crash there's no telling its correct.

This leads to a question do other debuggers such as Nsight even require this extension to give you source level debug?

## 12/16/2024 11:40:59 @ChristianReinbold

#5113 seems to boil down to the same problem, just for another type missing in the switch statement.

Regarding usage: NSight Graphics also claims to require the option, see [here](https://docs.nvidia.com/nsight-graphics/UserGuide/index.html) (search for -fspv-debug=vulkan-with-source). This is what I am interested in.


## 12/16/2024 11:47:23 @ChristianReinbold

Regarding options `source` and `tool`: They behave differently than `vulkan-with-source`, see [HLSLOptions.cpp:1213](https://github.com/microsoft/DirectXShaderCompiler/blob/d39324e0635130e834a68e33b0c603cf5fc9fb4f/lib/DxcSupport/HLSLOptions.cpp#L1213). As far as I see it, the flag that results in entering the broken code-path is `opts.SpirvOptions.debugInfoRich = true`.

It does not seem surprising that SpirV intrinsics work. I have not checked, but I would assume that DXC does not even try to generate some meaningful debug info for it.

## 12/16/2024 13:41:36 @devshgraphicsprogramming

> [#5113](https://github.com/microsoft/DirectXShaderCompiler/issues/5113) seems to boil down to the same problem, just for another type missing in the switch statement.
> 
> Regarding usage: NSight Graphics also claims to require the option, see [here](https://docs.nvidia.com/nsight-graphics/UserGuide/index.html) (search for -fspv-debug=vulkan-with-source). This is what I am interested in.

Good to know that NSight debugs the same way.

## 12/16/2024 13:50:50 @devshgraphicsprogramming

> Regarding options `source` and `tool`: They behave differently than `vulkan-with-source`, see [HLSLOptions.cpp:1213](https://github.com/microsoft/DirectXShaderCompiler/blob/d39324e0635130e834a68e33b0c603cf5fc9fb4f/lib/DxcSupport/HLSLOptions.cpp#L1213). As far as I see it, the flag that results in entering the broken code-path is `opts.SpirvOptions.debugInfoRich = true`.
> 
> It does not seem surprising that SpirV intrinsics work. I have not checked, but I would assume that DXC does not even try to generate some meaningful debug info for it.

Actually seems like even with Spir-V intrinsics it will segfault.

## 12/16/2024 15:38:36 @keptsecret

@devshgraphicsprogramming @ChristianReinbold 
Here's the version that used HLSL syntax ray query: https://tinyurl.com/44ycvrmu

## 02/11/2025 19:59:46 @s-perron

@ChristianReinbold Can you open a PR if you already have a patch? We just need some tests. We may get to this soon, but it could be faster if you open the PR.

## 02/12/2025 08:05:52 @ChristianReinbold

@s-perron See PR [#7139](https://github.com/microsoft/DirectXShaderCompiler/pull/7139). It is still lacking a test though. If you can give me a quick pointer to a test directory where I can reformulate my reproducer as a test, I will add it. 

## 04/02/2025 18:17:32 @NoSW

I used the latest version(v1.8.2502, 2025_02_20) and had this bug (a mini test case #7300). What's confusing is that even the latest version of dxc can't compile ray tracing shader with `-fspv-debug=vulkan-with-source` , but the Nsight doc directly says 
> To enable function debug information in SPIRV, which is the dependency of Flame Graph, Top-Down Calls and Bottom-Up Calls, we need to add the argument -gVS (instead of -g) for glslangValidator **or `-fspv-debug=vulkan-with-source` for `dxc`, to enable the SPIRV NonSemantic Shader DebugInfo extension.** 

How did they test it? 😢

## 04/04/2025 14:20:29 @pborsutzki

> How did they test it? 😢

E.g. with [Slang](https://shader-slang.org/). Looks like Slang currently is Nvidias preferred shading language. Also, you don't need a raytracing shader to test callstacks, you can also just use a non-raytracing compute shader 😉

But for me, even with the patch from #7139 Nsight fails to show me callstacks - but for different reasons (it says it has no debug info at all).

## 08/19/2026 03:23:11 @NoSW

The test case https://github.com/microsoft/DirectXShaderCompiler/issues/7300 is passed since  v1.9.2602. So does RayQuery with `-fspv-debug=vulkan-with-source` is already supported? 

I cant find any related info in ReleaseNotes 

