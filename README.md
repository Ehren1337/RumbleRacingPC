# RacingRumblePC

Experimental **Rumble Racing USA retail PC port**, built with a modified [PS2Recomp](https://github.com/ran-j/PS2Recomp). Current Windows testing reaches menus, vehicle/track selection, races, laps and results. Busy scenes still slow down; some rendering/audio issues remain. This is a source project, not a finished downloadable game.

## What this repository preserves

- The pinned runtime/recompiler patch, including our native geometry, graphics, audio and retail development integrations.
- The exact retail function boundaries, selected names and runtime bindings needed to regenerate the tested game code. Ghidra is not required to build this supported revision.
- A build/launch script and hashes that verify all **2,144 generated C++/header files** against the working port before installation. The comparison normalizes line endings.

**No game executable, assets, generated/decompiled game code, prototype linker map, saves or binaries are included.** You supply your own extracted disc. Game code is generated locally from that executable; this is not the original developer source. Prototype symbol matching and debug/content restoration are **unfinished**, not fully transferred.

## Requirements

- Git, Python 3.10+, CMake 3.21+, and a C++20 compiler. Tested on Windows with Visual Studio's **Desktop development with C++** workload.
- The matching USA retail extracted disc, keeping `SLUS_201.74`, `GLBLDATA.PS2`, `DATA/` and `MODULES/` together. The script verifies the executable and AUDIO.IRX hashes in `port-lock.json`; a matching filename alone is insufficient. It does not extract or download games, and those two hashes do not validate every asset.
- Default graphics: DiligentCore/D3D11. Default movie decoding: FFmpeg development libraries. CMake downloads configured dependencies on Windows. Other hosts need their native development dependencies; Linux/macOS gameplay is unverified. The project aims at a cross-platform port, not verified support everywhere.

## Build and play

Run from this repository's root:

```sh
git clone https://github.com/Ehren1337/RacingRumblePC.git
cd RacingRumblePC
python -B port.py setup
python -B port.py generate --disc "<EXTRACTED_DISC_DIRECTORY>"
python -B port.py build
python -B port.py run
```

On Windows, `py -3 -B` can replace `python -B`. Replace the disc placeholder with your own directory, not an ISO/BIN filename. Setup pins upstream revision `14b1e5cb39b4af7e6fc12f9a29fdc751efde49d7` and applies the included patch. Generation builds the recompiler, verifies the output, and stages it into the engine's existing runner source directories. Build then creates the native executable. It uses one `RelWithDebInfo` build and leaves independently edited files alone.

On Windows, the script enables Git long-path handling only for its child processes so nested dependency files can be checked out. It does not change global Git settings. A short checkout path is still advisable for compiler/build-tool path limits.

The default engine location is `.engine/PS2Recomp`. To reuse an existing matching patched checkout and build instead, start with `python -B port.py setup --source "<EXISTING_PS2RECOMP_CHECKOUT>"`. It verifies the source instead of resetting it. Local paths/state live in ignored `.port/`; generated source and builds remain inside the selected engine checkout. Deliberate source changes require reviewing/updating the recipe locks; checks are intentionally strict.

Optional setup flags: `--cpu-renderer` disables Diligent; `--no-ffmpeg` builds the current placeholder movie path, not an alternate decoder. These are not equivalent to the tested default experience. On Windows, CMake can use an existing FFmpeg SDK via `PS2X_FFMPEG_ROOT`; non-Windows builds need FFmpeg development packages (`libavcodec`, `libavformat`, `libavutil`, `libswresample`, `libswscale`) when enabled.

## Development controls

Normal `run` uses manual controls and the original menus. These options apply only to the supported retail build:

```sh
# Tiberius (driver 6), True Grits (track 10), original race loading:
python -B port.py run --car 6 --track 10
# Import your own PCSX2 keyboard bindings; the profile is read only:
python -B port.py run --keyboard-profile "<PROFILE_DIRECTORY>/Keyboard.ini"
# Optional original NPC player driving and player-only upgrades:
python -B port.py run --car 6 --track 10 --ai --max-upgrades
```

`--spot "<SAVED_POSE.json>"` accepts the validated private pose format from our development tools and teleports three game seconds after GO on its matching track. No pose is bundled and this script does not capture poses. The wider research/pose-capture tools are in [PS2RecompAIWorkflow](https://github.com/Ehren1337/PS2RecompAIWorkflow/tree/main/Rumble%20Racing); they are optional and have their own workspace conventions. Teleport restores a car pose, not the whole race state.

The visible window uses 1280x720 output with a 4:3 picture; that does not raise the game's internal render resolution. Images/viewer capture are off. Inspector JSON and two reused console logs stay in the selected engine's `out/build/ps2xRuntime/`. An AI assistant is not automatically connected; it must be given access to the source/report files. Other backend choices (`--gpu d3d12` or `--gpu vulkan`) need separate live validation; D3D11 is the current tested path.

## Verification and limits

The recipe regenerated all 2,144 files exactly from the verified retail executable, including the earlier handwritten RSQRT correction now produced by the translator. All 86 post-patch source files match the tested runtime snapshot. The dedicated script successfully built the existing Windows checkout and launched the original title screen without development race options. The existing Windows runtime suite previously passed **563/563** tests; this does not prove complete game compatibility. All six dedicated script tests passed, covering guarded staging, file ownership, pose validation and read-only process checks:

```sh
python -B -m unittest discover -s tests -v
```

`generate --check --disc "<EXTRACTED_DISC_DIRECTORY>"` verifies reproduction without staging files. `--recompiler "<EXISTING_RECOMPILER>"` reuses an already built compiler for that check. Output that does not match the locked port is rejected. The working Windows checkout has been reused for validation; a complete first-time dependency download/build on another computer has not been validated.

This repository preserves the current reproducible retail port recipe. It is **not a backup of private Ghidra databases, prototype research, assets, saves or local edits outside the published patch**. Keep those separately if you want to continue that research.

## Credits and license

Built on [ran-j/PS2Recomp](https://github.com/ran-j/PS2Recomp); the patch snapshot is also recorded in `port-lock.json`. GPL v3 applies to the distributed project code; upstream notices are retained in [LICENSE](LICENSE). CMake-fetched dependencies retain their own licenses. This does not license the game's original code/assets. Not affiliated with the game's publisher.
