# Porting research summary

Research baseline: September 23, 2026; published September 24. Target: Rumble Racing USA retail, `SLUS_201.74`; identity and source revision are recorded in [port-lock.json](../port-lock.json). February and March prototypes are comparison references, not substitutes for this retail executable.

## Reproducible baseline

An independent GitHub clone fetched the pinned engine and dependencies, built its own recompiler, reproduced all 2,144 locked C++/header files and built a new runner. The only game input was the matching extracted retail disc. No old build objects, generated files, saves or Ghidra project were copied. Normal startup, intro playback, menus, Silver Streak selection, True Grits loading and ordinary accelerator input passed on Windows/D3D11. Development race shortcuts, teleport, upgrades and player AI were off.

This found and fixed a Windows Git long-path dependency-checkout issue. It used an existing installed compiler/SDK toolchain; it was not a bare-machine installation test. See the [README verification details](../README.md#verification-and-limits).

D3D11, D3D12 and Vulkan libraries built in that clean checkout. D3D12/Vulkan gameplay was not checked in that clean-clone run. The handoff records earlier limited Vulkan gameplay observations and four-API shader tests; neither establishes complete backend/platform compatibility. DirectX 10 and production OpenGL game-window integration remain unfinished.

## Major retained work

- Recovered hot VU geometry behavior into seven guarded native C++ paths, with bounded reference comparisons and preserved state, rounding, cycle and packet behavior. Unsupported cases still require the interpreter.
- Added shared DiligentCore GS rendering, ordered submissions, coherent transfers and display extraction. Diligent supplies the graphics API abstraction; the PS2 GS behavior remains project code.
- Reduced transfer/synchronization work, including early depth readback for a verified visibility sequence; restored native geometry during results rendering.
- Fixed instruction/translation and graphics correctness defects, including RSQRT.S handling implicated in incorrect object shadows. The current generator reproduces that correction without a manual generated-file edit.
- Repaired encountered audio/service progression and reply-ownership issues. The shared audio implementation and driver coverage remain incomplete.
- Added bounded diagnostics, object/command attribution, Python research helpers and repeatable direct-race/pose development hooks. The helpers are in the separate workflow toolkit; the native hooks are in the published patch.
- Reduced GS lookup storage from 2.75 MiB to 88 KiB without changing texture quality. This memory reduction alone does not establish frame-time or power savings.
- Retained constructed spare DMA-buffer ranges instead of repeating initialization. A small-payload synthetic chain fixture improved from approximately 7.00 to 4.85 ms; large-payload improvement was not established. This is not a whole-game FPS claim.

The [simulation handoff](../RUMBLE-RACING-SIMULATION-HANDOFF.md) records measurements, contracts and rejected experiments in more detail. Its historical 563/563 runtime-test result is separate from the clean-clone launch check and the seven build-script tests.

## Remaining investigations

1. **Busy-scene slowdown:** native geometry/command preparation, renderer buffer updates and graphics transfer/completion waits remain concrete targets. No single barn, plane, pickup or audio event explains all observed slowdowns. Attribute deferred work and control camera/world state before making object-specific claims.
2. **Correctness and transitions:** name-entry panel artifacts, remaining clipping/texture-state cases, additional vehicles/tracks, results, restart/replay and longer sessions need coverage. A successful race-start check is not exhaustive acceptance.
3. **Portability:** run on other intended hosts/backends and test actual gameplay. CPU-side display extraction/upload remains part of the current window path.
4. **Debug restoration:** console initialization/input/display references exist in February, but retail font layouts differ. A read-only Python equivalent of the TRAILS diagnostic was investigated; this is not the original console restored in-game.
5. **Earlier content:** February has changed vehicle/object payloads worth comparing. March's indexed vehicle models match retail. `EXTRA2` model data duplicates `EXTRA1`; `DA4.TRK` references do not establish a recovered fourth track. DIAMOND versus PU_INNER may be a changed successor, not a wholly removed object. See the dated [asset findings](ASSETS-AND-DEBUG.md).
6. **Audio:** complete reusable services while retaining game-driver protocol boundaries. One driver's adapter cannot be assumed to cover every PS2 game.

## Continuing work

Start from the public recipe and your own matching game inputs. Record source/build identity, backend, flags, car/track, game-clock progression and host elapsed time. For performance claims, preserve the workload and compare repeated runs; do not substitute dropped effects, altered physics or faster clocks for less host work.

Use [the research index](README.md) for the published metadata and excluded evidence. This summary deliberately replaces the private chronological work log for sharing; it is not a line-by-line copy of that log or a claim that all prototype symbols/features are now in the retail port.
