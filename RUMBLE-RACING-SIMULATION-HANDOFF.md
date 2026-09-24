# Rumble Racing native port: simulation and rendering developer handoff

**Status: 23 September 2026. Experimental, working Windows development build; full-speed gameplay everywhere and cross-platform completion remain unproven.**

This document records the September 23 research baseline, the evidence behind the major improvements, and where another developer should continue. It contains no game assets, executable, generated/decompiled game source, private paths, or memory dumps. The runtime patch and retail build recipe are included in this repository; research tools are linked separately below. Raw captures and decompiler exports are not distributed.

## 1. Target, source baseline, and availability

- Target: **Rumble Racing USA retail, SLUS_201.74**. Preserve retail gameplay, physics, audio, and content.
- Retail ELF SHA-256: `e3c2c19b5fdeeac9fb1f5a9b893346e7892e564796fa2f74fc40ae17a8ade594`.
- February prototype symbols and February/March assets are research references. Matching the same SLUS filename is insufficient to identify a build. Prototype feature/content restoration is not finished.
- Upstream: <https://github.com/ran-j/PS2Recomp>, local base commit `14b1e5cb39b4af7e6fc12f9a29fdc751efde49d7` plus substantial working-tree changes.
- Port source: [locked runtime patch](patches/runtime.patch) and [build recipe](README.md). Separate research/navigation tools: [PS2RecompAIWorkflow](https://github.com/Ehren1337/PS2RecompAIWorkflow/tree/74c849130cda63af33095d50088152465139d266/Rumble%20Racing). Those tools have their own workspace layout and are not installed by this Markdown file.
- Historical runtime suite: **563/563 tests passed**; the fresh-clone check built the runner and exercised gameplay rather than rerunning this whole suite. Latest deployed geometry changes also passed bounded live interpreter comparisons.

Use this repository's locked patch and generate the game-dependent inputs locally from the matching disc. The [fresh-clone verification](README.md#verification-and-limits) reached normal-menu gameplay without the private Ghidra project or old build. Linux/macOS, production OpenGL integration, and DirectX 10 support are not established by the Windows results.

Engine paths below use this repository's default `.engine/PS2Recomp/` checkout; substitute your selected source directory if using `setup --source`. References to `tools/`, `Scripts/`, and `Inspect-Runtime.ps1` describe the separately linked workflow toolkit, not files bundled here. Its commands require its documented layout and matching locally supplied inputs.

## 2. What currently works, and what “slow simulation” means

The development build reaches menus, vehicle/track selection, loading, races, manual driving, laps, race completion, and results. Multiple vehicles/tracks have been exercised. This is not an exhaustive content or transition matrix.

The game clock normally advances **1,200 ticks per host second**. This is the rate of the measured clock, not a claim that the game runs 1,200 physics updates per second. We use:

```text
simulation rate = game-clock tick delta / host monotonic elapsed seconds
speed percent   = simulation rate / 1200 * 100
```

A window reporting 60 FPS can still show slow-motion gameplay. Presentation rate and game-clock progress must be measured separately. Do not “fix” this by increasing the clock, skipping physics, dropping effects, or changing game rules.

Earlier observed scenes ran around 21–29% of normal speed. Later optimized scenes reached approximately 100%. Recent busy driving windows still measured roughly 71–83%. These observations span different scenes/builds and are **not a deterministic whole-game speedup ratio**.

## 3. Execution and rendering architecture

```text
Retail EE program -> generated native C++ functions -> PS2 runtime services
                                                     |
                                             DMA / VIF uploads
                                                     |
                  verified native VU routines <-> VU interpreter fallback
                                                     |
                                                GIF packets
                                                     |
                                                GS frontend
                                                     |
                        ordered worker queue -> Diligent GPU GS operations
                                                     |          |
                                             CPU fallback    GPU VRAM
                                                     |          |
                                          coherent transfers / display extraction
                                                     |
                                         host image -> raylib game window
```

The GPU implementation is a custom PS2 GS implementation using **DiligentCore**, not the whole Diligent engine. DiligentCore is pinned to `b37336e5aac0c944a6d8f51b9f453ba3813738b5`. It provides API abstraction; it does not supply PS2 rendering semantics automatically.

Current live gameplay uses D3D11. Shared GPU tests exercise D3D11, D3D12, Vulkan, and OpenGL on Windows. This does not establish playable game support on every API or operating system. The rendering path implements GS behavior in GPU shaders and keeps CPU reference/fallback behavior where needed; it is not a replacement of the original game with a conventional modern material/mesh engine.

Display extraction still produces a CPU-side frame which raylib uploads for display. **Direct GPU-to-window presentation is unfinished.** FFmpeg libraries handle supported movie decoding, not race rendering or general PS2 sound-driver execution.

## 4. Major improvements and breakthroughs

| Work | What changed | Evidence and practical limit |
|---|---|---|
| Native VU geometry | Recovered selected hot microprogram behavior and implemented direct portable C++ calculations, avoiding instruction dispatch in supported cases. | Earlier live checks reached 256 successful comparisons for each of the seven paths; subsequent checks remain bounded. Unsupported cases retain the interpreter. |
| GPU rendering | Added shared textured/color/depth/blending/fog/palette operations, ordered batching, and CPU fallback/coherence rules. | Common GPU tests pass on four Windows APIs. A synthetic 4,096-triangle D3D11 workload fell from about 16.6 ms to 1.2–1.9 ms including completion/readback. This is not gameplay FPS. |
| Less CPU–GPU transfer waiting | Kept supported local copies on GPU, tracked coherent VRAM pages, extracted display pixels rather than downloading all VRAM, separated FINISH completion from full host coherence, and deferred display readback. | Removed several unnecessary transfers and synchronization points without discarding rendering work. One 512×224 display extraction is 458,752 bytes instead of a 4 MiB full-VRAM download; other transfers still occur. |
| Early depth readback | Recognized the game's small depth-copy/read sequence for visibility/sun-flare work and queued an early GPU snapshot into a reusable 64 KiB buffer. | Same-process OFF/ON/OFF/ON observations: about 1,013 / 1,173 / 1,002 / 1,193 ticks/s. This was the clearest step toward normal-speed gameplay in that tested scene. Traffic still varies between windows. |
| Results-screen regression | Results were continuing to render the track but disabling native geometry, sending that work back through the interpreter. Added independently validated results-phase native execution. | Observed results rates progressed from roughly 496–523 to 906–922 ticks/s after the changes. Different frames/particle counts prevent claiming an exact causal percentage. |
| VU scheduling and arithmetic | Reduced redundant FMAC work, cached bounded matrix preparation, and grouped idle XGKICK transfer cycles while preserving exact completion timing. | A controlled earlier FMAC A/B gave about 3% game-clock improvement in its scene. Idle-transfer synthetic benchmark used about 78% less processing time. Neither number applies universally. |
| Recent bounded arithmetic | Once bounded transforms have accumulated both sign/zero sticky flags, stop recalculating those flags while preserving separately rounded products/sums and ACC. | Clipping: about 24% less routine time on a 64-vertex fixture. Latest 1428 path: about 27% less on a 72-vertex fixture compared with the preceding implementation. Both are isolated benchmarks. |
| Correctness repairs | Fixed recovered instruction/translation and rendering defects, including the RSQRT.S source/operation error affecting object shadows, and earlier missing road/water/clipping issues. | User confirmed the shadow fix. These correctness changes matter independently of speed; do not classify every artifact as culling or bandwidth. |
| Audio/progression repairs | Implemented verified retail driver requests, stream/reply ownership, engine/effect behavior, and alternate-engine requests that had caused stalls/freezes. | Removed encountered progression blockers. Complete audio-driver compatibility remains unfinished. |

Memory work also reduced the GS lookup tables from **2.75 MiB to 88 KiB**, without reducing texture quality. Memory-size reduction alone is not proof of faster frames or lower power.

## 5. Native VU paths and correctness contract

| VU entry PC | Current handwritten native behavior |
|---|---|
| `0x1428` | Main transform/projection/packet construction |
| `0x1618` | Geometry transforms and supported clipping/control paths |
| `0x0B38` | Reflection geometry |
| `0x0400` | Lighting geometry |
| `0x0840` | Combined reflection/lighting |
| `0x0DB0` | Dual-basis projection |
| `0x24C0` | Quad path |

These are Rumble-specific specializations guarded by program identity and execution/input contracts, not general replacements for all PS2 VU programs. Python models in `tools/rumble_vu_research.py` were used to understand and compare behavior before portable C++ implementation.

The native path must preserve packet and scratch-memory contents, VF/VI/ACC/scalars, sign/zero/sticky flags, guest cycles, XGKICK issue/drain timing, branch/exit state, and caller floating-point environment. Input memory must remain unchanged where the pure model promises that. Separate multiply/add rounding is intentional: do not enable fast-math or fuse these operations into FMA.

Current arithmetic is compiled with `/fp:strict` on MSVC or `-frounding-math;-ffp-contract=off` elsewhere. Non-Windows compilation/runtime behavior still needs validation.

Startup gates require 128 successful comparisons before enabling supported native execution; additional checks are spread over execution up to 256. Racing/results have independent gates. Mismatches disable the corresponding native path. These bounded checks establish the sampled cases, not every possible later input. A `rejected` counter means a guard selected fallback; it is not the same as a comparison failure.

Latest deployed check: all seven paths **256 matched / 0 mismatched**. For 1428, 191,760 memory words were compared with zero register/contract failures. No fresh results-screen or cross-platform validation was performed for the latest arithmetic-only change.

## 6. What the remaining slowdown evidence actually says

The most recent complete 35-second busy-route timing sample preceded the latest 1428 arithmetic optimization:

- 29 one-second windows: about 1,157–1,217 ticks/s; five slow windows: 858–997; one middle window: 1,037.
- Worst window: about 858 ticks/s, 632 live particles, executor CPU about 89% of one core, renderer thread about 41% of one core.
- VU1428 aggregate: about 224 ms across 34,380 calls in that host-second window.
- VU1618 aggregate: about 132 ms across 12,927 calls; native clip math counter about 56 ms across 12,461 executions, with 466 guard fallbacks.
- Lighting and other geometry paths remained substantial.

**VU aggregate durations include downstream GIF processing and possible renderer backpressure.** Do not add them to overlapping renderer time or call them pure arithmetic costs. Native packet-builder timers, call stacks, and transfer timing answer different questions.

Recent native sampling showed geometry math, VIF decoding, and synchronization. VIF was roughly 5% of sampled executor residence in one run. Its hot-loop samples mostly involved masked V2/V3-32 and unmasked V4-8, not plain bulk V4-32 copies. A raw V4-32 memcpy fast path therefore would not address most observed work.

Stack walking distinguished normal `EeScheduler::waitForEvent` pacing from `GSDiligentBackend::Present` waits. Removing all waits would be incorrect. A synthetic GIF queue experiment found only about 0.11 microseconds incremental queue/copy cost per 193-qword packet in that fixture; that did not justify a major queue rewrite.

The guest PC frequently remains at `0x12C3DC` while a VIF1 DMA-start write performs synchronous host graphics work. That identifies the call boundary, not an expensive MIPS store or proven guest busy loop.

### Plane, pickups, and particles

True Grits' plane was identified as `SE_CROP_DUSTER.O3D`, associated with the `DUSTER` network actor. Plane CPU command preparation measured only about 1.7–9 microseconds per call in sampled conditions. That step alone does not explain the slowdown.

Its deferred geometry/GPU contribution is not isolated. Object-list membership does not prove pixel visibility. Particle count, pickups, cars, scenery, and camera position change together; correlation is insufficient to blame any one object. Do not remove the plane, effects, or geometry to manufacture a faster benchmark.

### September 23 measurements and retained changes

- **Ordered submission batches:** GS gathers at most 16 completed compatible draw records and flushes before state/transfer boundaries. The Diligent backend amortizes submission locking/rounding lookup while retaining owned snapshots and draw order. Synthetic reference tests cover queue wraps, state changes, caller-memory reuse and exceptions. Small queue benchmarks were noisy; do not claim a universal frame-time reduction.
- **Exact register-key comparisons:** portable word-wise XOR/OR replaces repeated general-purpose memory comparison on 8-, 9- and 22-word keys, preserving all bits and invalidation. Two-million-comparison fixtures improved approximately 46-55%; the key cache remains 136 bytes. This is an isolated operation, not a 46-55% gameplay improvement.
- **More precise attribution:** bounded object-instance/model IDs, producer callsites and submitted-tag ownership connect selected CPU/VU work to assets. Shared/reused buffers and unowned commands remain explicit. A model's construction time is not its total GPU cost; an object label is not by itself causal proof.
- **ETW wait evidence:** a slow stationary trace placed about 298.5 ms of executor blocked time in BeginTransfer over a three-second interval. Stacks resolve the original sun-flare depth visibility download and prefetched depth mapping. A separate full-VRAM fallback hitch also occurred; its triggering draw remains unidentified. Do not merge those two mechanisms.
- **Moving trace:** a later CPU+GPU capture found native geometry/submission pressure, renderer UpdateBuffer stalls and graphics completion dependencies. Hardware queue pending intervals include scheduling and notification, not just GPU shader execution. A GPU completion immediately preceding a blocked transfer's wakeup supports a real dependency; removing the wait would risk stale depth data.
- **API comparison:** both D3D11 and Vulkan reproduced the farm slowdown. D3D11's sampled course80-120 median/minimum were 93.3%/81.8%, Vulkan 78.7%/66.6%, but NPC state and race timing differed. These are provisional route observations, not controlled API speedup claims. A later D3D11 run with verbose GPU profiling off still dipped to 83.3%.
- **Rejected experiments:** an extra roughly 694 KiB alternating upload-buffer set reduced submission time but worsened the immediate-dispatch fixture's end-to-end median from about 28.9 to 34.7 ms; it was removed. A queue worker copy-elimination experiment also lacked a reliable gain and was reverted. Do not reintroduce either merely to lower one isolated counter.

The strongest remaining targets are CPU geometry/command preparation and graphics transfer/completion dependencies. No single barn, plane, pickup, audio event or missing multicore switch has been proven to explain every slowdown. Normal GPU profiling is off; verbose timestamps and thread-stack sampling add overhead.

Numeric profiling can use `tools/rumble_profile.py --trigger slowdown --pre 3 --seconds 15`; enable PS2_VU_PROFILE before launch. Optional `--objects` needs PS2_RUMBLE_OBJECT_PROFILE. `--stacks --stack-lines` records bounded thread pauses. WPR/xperf collection through `tools/rumble_etw.py` needs administrator rights and performs a bounded farm drive; `--gpu` adds graphics events. Reuse existing reports/trace. The last combined ETL was roughly 3.59 GB, so prefer focused reanalysis and shorter future collection rather than accumulating traces. Preserve PID/thread IDs, captured interval and build identity when comparing with live counters.

## 7. Source map

| Area | Relevant files |
|---|---|
| Game-specific native VU work | `.engine/PS2Recomp/ps2xRuntime/src/lib/rumble_vu_native.cpp`, `include/rumble_vu_native.h` within the same runtime directory |
| Interpreter, scheduling, transfers | `.engine/PS2Recomp/ps2xRuntime/src/lib/vu/ps2_vu1_core.cpp`, `ps2_vu1_upper.cpp`, `ps2_vu1_detail.h` |
| VIF/data movement | `.engine/PS2Recomp/ps2xRuntime/src/lib/ps2_vif1_interpreter.cpp`, `ps2_memory.cpp` |
| Shared GS frontend | `.engine/PS2Recomp/ps2xRuntime/src/lib/gs/gs_frontend.cpp` |
| GPU queue, coherence, CPU fallback | `.engine/PS2Recomp/ps2xRuntime/src/lib/gs/gs_diligent_backend.cpp` |
| GPU shaders, transfers, extraction | `.engine/PS2Recomp/ps2xRuntime/src/lib/gs/gs_diligent_device.cpp` |
| CPU reference and threaded backend | `.engine/PS2Recomp/ps2xRuntime/src/lib/gs/gs_cpu_backend.cpp`, `gs_threaded_backend.cpp` |
| GPU dependency/build options | `.engine/PS2Recomp/ps2xRuntime/cmake/DiligentGS.cmake`, runtime `CMakeLists.txt` |
| EE execution/pacing | `.engine/PS2Recomp/ps2xRuntime/src/lib/Kernel/EeScheduler.cpp`, `ps2_runtime.cpp` |
| Shared audio output/mixing | `.engine/PS2Recomp/ps2xRuntime/src/lib/ps2_audio.cpp`, `ps2_audio_vag.cpp`, `include/runtime/ps2_audio_reverb.h` |
| Driver-specific audio | `.engine/PS2Recomp/ps2xIOP/src/modules/rumble_audio.cpp`; existing other profiles in `src/builtin_profiles.cpp` |
| Development overrides | `.engine/PS2Recomp/ps2xRuntime/src/lib/rumble_dev.cpp`, `game_overrides.cpp` |
| Numeric inspector | `.engine/PS2Recomp/ps2xRuntime/src/lib/ps2_inspector.cpp`, `../tools/Inspect-Runtime.ps1` |
| Research/navigation | `tools/rumble_vu_research.py`, `rumble_menu_research.py`, `rumble_navigate.py`, `Scripts/rumble_dev.py` |
| Regression tests | `.engine/PS2Recomp/ps2xTest/src/ps2_vu1_tests.cpp`, `ps2_memory_tests.cpp`, `ps2_gs_gpu_tests.cpp`, `ps2_sif_rpc_tests.cpp`, `code_generator_tests.cpp` |
| Detailed local evidence | [public porting summary](analysis/PORTING-SUMMARY.md); the full chronological local log is not published |

PS2Recomp's recompiler, runtime scaffolding, and basic analysis facilities are upstream foundations. The inspector/viewer, research automation, Diligent backend, many runtime fixes, and native Rumble routines described here are local/custom additions. The Markdown file does not install them.

## 8. Reproduction and repeatable scene setup

Follow the repository [build instructions](README.md#build-and-play). The fresh-clone test supplies the matching extracted retail disc and builds the pinned source; Ghidra and the original private workspace are not required. Keep one build directory and close its runner before relinking.

```powershell
# Run from this repository root after setup, generation and build.
python -B port.py run
# Optional repeated benchmark setup, using original loading:
python -B port.py run --car 6 --track 10 --max-upgrades
# Optional private pose captured with the separate workflow tools:
python -B port.py run --car 6 --track 10 --spot "<SAVED_POSE.json>"
```

The default is manual driving and normal menus. Development upgrades are opt-in; keep the setting identical across comparisons. See `port.py --help` and `port.py run --help` for the actual supported public launcher options. Host 720p window sizing does not imply 720p internal rendering.

For research-only comparison runs, set `PS2_VU_PROFILE=1` and the necessary numeric profiling switches before launch. Presentation/depth comparison and verbose GPU timestamps add work; keep them separate from steady-state performance measurements. Do not benchmark during compilation. `port.py` sets its bounded native comparison defaults explicitly.

The following details describe the **separate workflow toolkit's** `Scripts/rumble_dev.py` interface (including named catalog selection, `--car-class`, `save-spot`, and `--benchmark-spot`), not additional `port.py` arguments:

Car and track accept catalog names or IDs; both arguments are required together. This opt-in adapter invokes original FE_PrepareRace (retail `0x1877d0`) and the original frontend loading handoff (event1974), after required initialization. It polls the startup card operation to completion, takes the original Continue/cleanup path, and omits intro presentation. It does not emulate button sequences. Ordinary launches retain normal menus.

Preset: one player, eight cars, three laps, Forgiving, power-ups active. `--car-class rookie|pro|elite` is available; the separate max-upgrades setting overrides player/opponent class as described above. Locked catalog selection is permitted in dev mode without editing save/unlock records. Live checks succeeded for Tiberius6/True Grits10 and Widow Maker2/Flip Out0 with neutral input, functioning race clocks and audio service updates; this does not certify every combination.

`save-spot` overwrites one ignored local `Scripts/rumble-benchmark-spot.json`. Matrix/game/track validation precedes use. `--benchmark-spot` schedules the original Vehicle_Reset at the player-input boundary, replaces only its matching placement query, and fires once at clock7200 after observing a fresh countdown (GO is clock3600; 1200 ticks/s). Fresh race restart rearms it. Original recovery updates dependent physics/collision caches. Live teleport, restart, camera settling and subsequent manual movement passed. AI plus teleport remains unverified.

The snapshot stores pose, not a full world state: NPCs, random state, race progress and lap progress are not restored; reset clears motion, active player power-ups and skid history. Do not reuse a route-node hint after teleport without checking it. Keep normal-input navigation for testing actual menus, not routine benchmark setup.

## 9. Tests and profiling

Run the suite from the nested checkout, where test resources resolve:

```powershell
cmake --build .engine/PS2Recomp/out/build --config RelWithDebInfo --target ps2x_tests
Push-Location .engine/PS2Recomp
$env:PS2_GPU_TEST_APIS='d3d11,d3d12,vulkan,opengl'
$env:PS2_GPU_VALIDATION='1'
.\out\build\ps2xTest\RelWithDebInfo\ps2x_tests.exe *> out/build/ntsc-tests.log
Get-Content out/build/ntsc-tests.log -Tail 10
Pop-Location
```

Focused filters/optional benchmarks, using the same executable:

| Filter | Optional environment switch | Purpose |
|---|---|---|
| `native packet candidate` | `PS2_RUMBLE_PACKET_BENCH=1` | 1428 output/state/rounding; current 72-vertex benchmark |
| `clip saturated sticky` | `PS2_RUMBLE_CLIP_FLAGS_BENCH=1` | Clipping flag optimization versus prior flag arithmetic |
| `XGKICK` | `PS2_VU_TRANSFER_BENCH=1` | Transfer boundaries, pending writes, timing and grouped idle cycles |

Use the established comparison/profile launch flags when reproducing the complete validation configuration. Separate correctness runs from steady-state timing: initial reference comparisons and shader compilation add cost. Never benchmark while compiling.

Recommended performance record: exact revision/diff, build configuration, GPU API/driver, CPU/GPU, launch flags, track/car/upgrades, phase, clock delta, monotonic elapsed time, position/camera/route, particles, per-thread CPU time, native/fallback counts, and display/readback metrics. Use A/B/A/B where possible and preserve workload. Report medians/ranges and scene variation rather than a single optimistic number.

Diagnostics available in memory include `ps2_vu_diagnostics::runProfile`, `rumble_vu::comparisonStats`, `nativeStats`, six `*NativeStats`, independent results counters, and `gs_prefetch_diagnostics`. Windows/PDB sampling is now in `tools/rumble_profile.py`; CPU/wait/GPU ETW recording and analysis are in `tools/rumble_etw.py`. The Markdown describes these separate source files; it does not embed their implementations. Thread sampling pauses must always be released; their overhead must be reported.

Inspector JSON is overwritten in place with bounded history. Check process identity, captured timestamp, sequence, and consistency—not just file modification time. A running process can publish an old snapshot. Guest addresses must be validated against the retail identity; host addresses and PIDs are never stable across restarts.

Viewer and automatic image capture are currently off for performance work. Optional contact sheets are multiple sampled frames arranged in one image, useful for temporal artifacts. They are not required for numeric profiling, and repeated file captures can perturb timing. Keep a small fixed set of outputs; do not grow frame dumps, histories, or build directories.

## 10. Audio: reusable core versus game-specific driver

A broadly reusable PS2 audio system is possible. The current implementation is not complete. It has shared PCM/sample output, streaming, 48-voice mixing, loop updates and reverb/effect support. Rumble's adapter translates recovered driver commands and asset-bank behavior into those facilities. Other games can have different command protocols; an adapter for one protocol is not automatically universal.

Two complementary routes are available:

1. Complete a shared IOP/SPU2 compatibility path capable of running/recompiling original drivers, including required module services, transfers, timing, interrupts, voices/envelopes/effects and memory behavior.
2. Reuse the shared mixer/output while adding validated adapters for supported driver families. Keep command decoding/game bank layouts in those adapters; avoid duplicating the backend.

The broader route is substantial runtime work, not just choosing another host audio library. PCSX2's source separates IOP execution and SPU2 components: <https://github.com/PCSX2/pcsx2/blob/master/pcsx2/CMakeLists.txt>. This is an architectural reference, not a claim that its code has been integrated here.

The intended architecture includes reusable common functionality for future games. The current Rumble adapter is a practical compatibility step, not the final definition of a universal backend. Preserve retail audio behavior and do not acknowledge unsupported commands as successful merely to bypass stalls.

## 11. Prioritized remaining work

1. **Sustained simulation speed.** Use direct car/track launch and the saved pose to repeat farm sections; account for NPC/world variation. Follow the measured geometry/submission and transfer-wait stacks. Preserve queued DMA ownership while investigating redundant copies; do not bypass work to raise the clock. Current isolated key/batch changes do not establish a whole-game speedup.
2. **Clipping fallback coverage.** Recover unsupported polygon-splitting/exceptional cases if profiles show they matter. Keep the existing correctness fallback until replacements match full state and timing.
3. **Presentation/transfer overhead.** Investigate remaining Present waits and eventual direct GPU-to-window presentation. Preserve ordering, coherent CPU reads, FINISH semantics, depth visibility, and texture/render-target alias rules.
4. **Object attribution.** Correlate plane/pickup/destructible draw preparation with deferred geometry/GS costs before declaring a cause. Existing plane preparation profiling excludes deferred work.
5. **Visual regression follow-up.** Name-entry/track-record panel black vertical streaks remain unresolved. Offline source/layout checks did not reproduce the defect; inspect its live loaded texture/state when available. Do not conflate it with the confirmed object-shadow fix.
6. **Transition/content coverage.** Exercise additional cars/tracks, loading, race completion, results, replay, restart and exit paths. Maintain independent results-phase native checks.
7. **Portability and backend coverage.** Build/run on intended operating systems and validate actual gameplay on supported APIs. Four Windows shader test backends are not a cross-platform acceptance test. DirectX 10 is not implemented.
8. **Audio/generalization and restoration.** Complete common audio behavior without losing the Rumble-specific verified commands. Prototype debug features, vehicles/handling variants and missing-content restoration remain separate unfinished goals; preserve retail audio/content as requested.

## 12. Acceptance criteria and sharing

A performance change is ready when focused regressions and the required suite pass, live native/reference or CPU/GPU comparisons remain clean, the original gameplay/visual behavior is retained, and improvement is demonstrated on an appropriately controlled workload. Synthetic gains must remain labelled as synthetic. A port is not complete until sustained gameplay, transitions, intended platforms/backends, audio and requested restored features have their own evidence.

Keep at most two or three build configurations, overwrite the existing logs/reports, and cap diagnostic history. Share this document with the corresponding current source patch and build instructions; do not include game assets, generated game code, binaries or private research dumps. Use the source snapshot and validation scope in the current README; earlier 508/544-test counts in old reports describe older revisions.
