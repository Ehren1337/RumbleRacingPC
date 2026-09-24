# Rumble Racing: debug systems and asset investigation

Research snapshot: September 20, 2026; prepared for publication September 24. These are findings from locally supplied February prototype, March prototype, and USA retail discs. Addresses and layouts are build-specific. The referenced raw JSON inventory and Ghidra analysis are not distributed; see [research scope](README.md). No original disc, extracted ELF, or game asset was modified. No recovered feature is claimed playable yet.

## Main findings

| Question | Finding | Confidence/limit |
| --- | --- | --- |
| Does March contain the missing `DA4.TRK`? | No. All three ELFs reference it; none of the three extracted file manifests contains it. March's original ISO directory also has no DA4 filename. | Confirmed filename/reference distinction. A complete fourth DA track has not been found. |
| Is there an extra test track? | Each build has the same 15 `DATA/LOC*/...TRK` paths. Each contains one `gmd ` track resource. Front-end TRKs also have a scene, including localized copies in March. | No additional complete test/race level identified in the parsed containers. This does not establish that every internal object or route is used. |
| Are `EXTRA1`/`EXTRA2` hidden removed cars? | Both have model assets in all three builds. The normal driver table maps Vortex to EXTRA1. EXTRA2 is not mapped by that table, but its A/B/C model payloads are identical to EXTRA1's corresponding payloads in every build. | EXTRA2 is duplicate model data, not evidence of a distinct recovered car. |
| Are there earlier vehicle assets worth preserving? | February has the same 111 vehicle model IDs as retail, but 58 payloads differ. March's 111 vehicle model payloads match retail. | Confirmed decoded model-byte differences; appearance and compatibility need a model viewer/gameplay validation. |
| Are prototype-only objects present? | Sixteen distinct stored O3D names have February payloads absent from the indexed retail resources by both name and decoded hash. Examples include `DIAMOND.O3D`, `NASRUM.O3D`, and several breakable/scenery objects. | Actual payloads, not only strings. Names do not alone establish purpose, appearance, or whether a changed/renamed successor exists. |
| Is the February debug console connected? | Yes. Initialization, main/front-end input updates, and display-list insertion have code cross-references. Fifteen commands are explicitly registered. | Static code paths verified; console operation and restoration on retail have not been exercised. Retail gameplay now runs; see [current porting summary](PORTING-SUMMARY.md). |

## Scope and validation

The read-only scanner walks SHOC streaming blocks and reconstructs each SHDR resource from SDAT and compressed Rdat blocks. The implementation was derived from February's `SM_ParseBufs` (`0x00127A60`), `loadStreamChunk` (`0x00127130`), and `Stream_DecompressChunk` (`0x00127690`). FILL blocks are skipped to the next 0x6000-byte streaming page, including four-byte FILL tails.

| Build | Disc files inventoried | Stream files parsed | Resource payloads reconstructed |
| --- | ---: | ---: | ---: |
| February | 68 | 30 | 5,103 |
| March | 104 | 34 | 6,588 |
| USA retail | 71 | 30 | 5,036 |

All 94 `.PS2`, `.TRK`, `.AV`, `.AV2`, and `.FLM` streams were walked without block errors. All 16,727 reconstructed resources reached their declared lengths without decoder errors. Their FNV-1a 64-bit payload digests matched those produced using the unchanged generated guest decompression function in an isolated native harness. SHA-256 hashes in the inventory are used for resource comparisons. This validates agreement with the recompiled decoder, not every assumption in PS2Recomp or every resource's game semantics.

All RLst resource lists also satisfied their count/size relationship: four-byte count followed by 32-byte records containing type, ID, and a 24-byte name field. Those stored names often contain only the tail of an original development path. The scanner associates resources with the preceding list's type/ID entries; names are retained verbatim.

March was checked directly against its original BIN: all 104 extracted filenames/sizes matched, and all 20 ELF/track/global-data files were SHA-256 verified against disc payloads. Earlier extraction checks verified February and retail. This rules out a WinCDEmu/extraction omission for the March DA4 filename.

The original, unpublished machine-readable evidence is in the local `assets-investigation.json`: manifests, archive offsets, resource types/IDs, decoded sizes and hashes, stored names, ELF strings, driver tables, comparisons, console registrations, and button bindings. It is overwritten on reruns. No thousands-of-files asset extraction was created.

## Tracks and test code

The 15 race-track container basenames in each build are BB1/BB2, BL1/BL2, DA1/DA2/DA3, JT1/JT2, MA1/MA2, MP1/MP2, and SE1/SE2. `DA4.TRK` is an ELF string in all three builds. No DA4 named resource was found in the decoded resource-list inventory. The February location table (`pTrackLocation`, `0x001F3D00`) has eight groups of three pointers, including a final DA group referencing DA3 and DA4. This makes DA4 a concrete planned/leftover reference, but not a recovered level.

Physics-test functions exist, but their bodies matter: `PhysicsTest_MakeTestObjects` (`0x0014C4F0`) immediately returns. `PhysicsTest_InitModule` (`0x0014C500`) clears `giNumTumblerRes`; it does not construct a test scene. The main loop does call the empty maker. Simulation/drawing helpers for existing test objects survive. These facts do not establish a complete hidden physics-test level.

The investigation has not reconstructed full track scene graphs, route connections, or visually inspected geometry. Some changed assets could represent earlier layouts within an ordinary track filename. That is a separate question from a missing standalone track.

## Vehicles

Each ELF has a verified 36-row driver table with 28-byte records. Model index is the byte at record offset 6; the loader uses it to select resource IDs `10000 + 3*modelIndex + variant`. The next word after row 36 is 5 in each build, not another valid name pointer. There are 111 distinct vehicle O3D IDs: 37 model groups with three variants each.

The unused group is model index 36, IDs 10108â€“10110 (`EXTRA2_A/B/C`). All three model hashes equal IDs 10105â€“10107 (`EXTRA1_A/B/C`), used by Vortex at model index 35. This comparison was checked independently within all three builds. It concerns O3D payloads; it does not by itself establish whether every texture or parameter is identical.

Six February names changed while their table slots/model indices stayed the same:

| February | March and retail |
| --- | --- |
| Demon | Maniac |
| Patriot | Revolution |
| Hornet | Stinger |
| Bago | Road Trip |
| Road Captain | Interceptor |
| Land Shark | XXS-TOMCAT |

These are evidence of renaming and earlier versions, not six additional absent vehicles. February model payloads offer a real restoration/comparison target: 53 of 111 match retail and 58 differ. All 111 March model payloads match retail. Corresponding textures, assembly behavior, collision/physics settings, and sound data must be checked before swapping a model into the retail target.

## Concrete earlier object candidates

These are stored names associated with decoded `o3d ` resources in February and absent from the indexed retail resources by both name and decoded SHA-256. Truncated path prefixes are intentional, as stored on disc. IDs are scoped to their containers/resource groups.

| Container | ID | Stored name | Decoded bytes |
| --- | ---: | --- | ---: |
| GLBLDATA.PS2 | 5011 | PS2:OBJECTS:DIAMOND.O3D | 5,520 |
| DATA/LOCMP/MP1.TRK | 42 | :RESOURCES:NASRUM.O3D | 976 |
| DATA/LOCMP/MP1.TRK | 36 | :RESOURCES:RUML.O3D | 1,104 |
| DATA/LOCMP/MP1.TRK | 38 | :RESOURCES:RUMM.O3D | 1,040 |
| DATA/LOCMP/MP1.TRK | 40 | :RESOURCES:RUMR.O3D | 1,040 |
| DATA/LOCMP/MP1.TRK | 37 | ESOURCES:RUML_BREAK.O3D | 3,872 |
| DATA/LOCMP/MP1.TRK | 39 | ESOURCES:RUMM_BREAK.O3D | 2,464 |
| DATA/LOCMP/MP1.TRK | 41 | ESOURCES:RUMR_BREAK.O3D | 6,016 |
| DATA/LOCMP/MP1.TRK | 1 | :RESOURCES:WIN.O3D | 13,600 |
| DATA/LOCSE/SE2.TRK | 1 | :RESOURCES:POWERUP.O3D | 5,728 |
| DATA/LOCSE/SE2.TRK | 11 | :RESOURCES:SE_CRATE.O3D | 1,792 |
| DATA/LOCSE/SE1.TRK | 8 | :RESOURCES:SE_TIRE.O3D | 5,984 |
| DATA/LOCSE/SE1.TRK | 9 | ESOURCES:SE_HAYBALE.O3D | 1,792 |
| DATA/LOCSE/SE1.TRK | 35 | URCES:SE_CROSSING_A.O3D | 4,704 |
| DATA/LOCBB/BB2.TRK | 19 | RESOURCES:PALMTREES.O3D | 28,160 |
| DATA/LOCMP/MP2.TRK | 26 | SOURCES:CRATE_BREAK.O3D | 11,936 |

DIAMOND's SHDR is at file offset `0x000A1A10` in February GLBLDATA.PS2. Its decoded SHA-256 is `0FBFBC9F630419D2C174F6D83BABD8400C0CCF7A54EDC3AC56D1AFF4BCAEA8D9`. No matching named/hash payload was found in March or retail. Its visual form and gameplay role remain unverified.

There are 258 distinct February name/hash candidate rows absent from retail by those two tests, including actor instances and sounds. That count is not 258 distinct removed gameplay features. Actor names can change through renumbering or rebuilding. March's 55 such candidate rows are localized front-end material in this comparison, not new vehicle models.

## Debug console audit

Confirmed cross-references in February:

| System | Evidence |
| --- | --- |
| Startup | `MA_vOnceInit` calls `CO_vInitModule` at call site `0x00124A24`. |
| Race loop input | `RB_vGameLoopHandleConsole` at `0x001699F0` tail-jumps to `CO_vManage`. |
| Front-end input | `RB_vRunFrontEndLoop` and `FE_FrontEndLoop` call `CO_vManage`. |
| Rendering | `RB_vGameLoopHandleDisplay` and `FE_FrontEndLoop` call `CO_vAddAllToDisplayList`. |
| Keyboard | Init selects input mask 2. `CO_vManageKeyboard` checks bit 2; controller handling checks bit 1. USB keyboard init/info/read/sync calls remain. |

The fifteen statically registered commands are `FPS`, `POLYINFO`, `POLYCNT`, `VURCNT`, `OBJCNT`, `MEM`, `TRAILS`, `DUMP`, `CHKSUM`, `DISP`, `VU1`, `SHOW`, `LINES`, `SET`, and `HELP`. Each has an explicit callback address in the unpublished local JSON report. The display command controls named rendering categories; the memory/checksum commands inspect address ranges; console presentation/history/input helpers are present.

Twenty-six predefined button bindings were decoded, including command strings with trailing newlines and editing control characters. Their device/code pairs are preserved in that unpublished report. Keyboard binding codes operate after the game's character conversion, so they should not be presented as raw USB keycodes without further mapping. An `AUDIOP` shortcut string exists, but no corresponding registration appears among the fifteen calls to `CO_vRegisterCommand`; it is a leftover lead, not a verified working command.

The console starts hidden, with seven lines and keyboard input selected. The initialization path and its data structures provide a much stronger restoration starting point than copying isolated command strings. Retail command-string absence alone is not proof of equivalent code removal; matching the surrounding engine interfaces is still necessary.

## Next implementation priorities

September 20 TRAILS diagnostic: February CO_boTRAILSCommandCall17E750 only prints the current light-trail manager's reserved-slot count at+C against capacity500; it does not enable/disable trails. Python normalized opcode matching finds exact structural counterparts for LT_vInitModule1C1E40 ->retail1BE3A0, LT_iGetLightTrail1C1EE0 ->1BE440, LT_vManageAllLightTrails1C2100 ->1BE660, and LT_vRenderAllLightTrails1C2BA0 ->1BF100. Read-only Ghidra confirms retail manager-pointer global1ED8E8, header(buffer allocation,index,current buffer,reserved count), two57E50-byte buffers inAFCA0 bytes, and500 entries of2D0 bytes per buffer. Layout was checked independently rather than inferred from the normalized match.

The separate workflow toolkit Python helper exposes `rumble_navigate.py debug-status` as an external read-only equivalent of TRAILS. Live retail PID4268 atclock287980 had manager1F4B20, buffers9DA060,index0,current9DA060,count407. The CLI independently returned407/500. It validates the retained car/track, consistent manager header, allocation bounds, buffer selection and count; in-memory checks accepted both buffers and rejected invalid layouts/counts. This restores access to one prototype diagnostic through Python; it does not restore the original console, render its overlay, or prove that407 trails are currently visible. No game memory/assets/native code were changed. DISP and VU1 callbacks were read but their retail interfaces have not been mapped: DISP changes named category bits; VU1 cycles callback-owned state0..2 rather than directly selecting an emulator backend.

September 20 interface check: Python normalized instruction matching found exact structural matches for February `FO_vAddStringToDisplayList` (12EAD0, 215 words) at retail12B3A0, and `FO_vAddAllToMainDisplayList` (12EE30,64 words) at retail12B700. This masks immediates and is NOT proof of identical layouts. Read-only Ghidra confirms retail font-manager pointer1E9AB0, current font at+D8, queued string array pointer+34, per-font queue stride1C404 and string entry stride1C4; ten font slots are flushed. The February manager has eleven slots, queue pointer+38 and current font+DC. February12EA90 maps font -1 to debug slot10; retail12B370 stores its argument directly. Copying the console's -1 selection or February field offsets would therefore be unsafe.

February12E870 allocates136C2C bytes for eleven font queues and loads its built-in font into slot10. Retail12B190 allocates11A828 for ten queues, defaults to slot0, and omits that default-font load. Its loader survives at12B140 and uses embedded stream1DC7C0, but its use as a restored debug font has not been validated. A restored display must use a valid retail font slot, preserve the current rendering context, and honor retail queue limits; do not append an eleventh slot to the existing allocation. Retail12B700 has a verified call at166E74 inside166D00 before display-list submission, as well as frontend and loading-loop callers. No hooks, symbol imports, memory writes or restored console were added by this analysis. No strong normalized matches were found for the two prototype FPS timer helpers in the searched exported function ranges; this is not proof that their behavior is absent.

February's INTRO.FLM was verified to contain NASCAR footage. Its originating NASCAR title remains unconfirmed. The exported movie and disc assets are not distributed in this repository.

1. Continue validating USA retail startup/audio interfaces; it is now the primary execution target. The February runner is a reference build, not the deliverable; do not require further February-only playback work without a demonstrated retail dependency.
2. Map the retail engine interfaces needed by February's console, then restore and validate one debug feature on retail. Use February's symbols and behavior as evidence; its console need not be fully polished first.
3. Add a read-only model/scene decoder or viewer for the sixteen earlier object candidates and changed vehicle meshes. Preserve material/texture/physics associations when evaluating restoration.
4. Compare route and scene contents within the existing track containers. Do not fabricate DA4 from its filename reference.

The native runtime inspector remains enabled with bounded, overwritten outputs. Retail has verified menus, vehicle/track transitions, rendered driving and a full lap on Car Go. At this historical snapshot, full race completion had not yet been verified. Later race/results progress is covered in the current summary; sustained real-time performance, cross-platform execution and prototype feature restoration remain incomplete. The latest runtime state is in [current porting summary](PORTING-SUMMARY.md); these asset findings remain static disc/code evidence rather than proof that the earlier content has been restored.

## Model interface audit (September 20)

Read-only tree/material query was performed with the separate workflow toolkit helper: `py -3.14 -B tools/rumble_research.py model --build February --id 10061` (also Retail). It validates the ELF identity and decoded model SHA256 against the independent inventory, walks Part/Gmd/Obf nodes, reports original object slots and relative texture-group/texture-ID references, and hashes raw object payloads. It does not resolve texture groups, decode vertices, install variants, or transfer handling. No extraction/output files are created.

Retail12C970 establishes the ELHE96-byte node header, signed child/material counts, padded ELTL index-list extent, ELDA word stream and recursive child order. The material list's declared byte size includes padding; using active-entry count alone was rejected by the real corpus and corrected to match the original parser. Texture pairs reside at packet-relative indexed word+0/+16 before relocation; group-1 means no texture relocation. Retail164550 still needs inspection to map relative group references to actual resident groups. The query rejects unknown headers and malformed bounds rather than assuming universal model compatibility.

Validation: all111 vehicle models plus5011 in each build pass (224 independently hash-checked resources). Broader global scan accepts121 February/122 retail resources and rejects19 nonvehicle raw-header variants per build; those formats are not supported by this query yet. Five in-memory malformed cases reject truncated input, zero chunk extent, wrong raw version, wrong node count, and negative child count. Retail CLI-query path also succeeds. Fragment records are structurally derived from169BA0 but no ExpF records occurred in this corpus; no live fragment restoration claim.

COMPACT_B10061 contains11 objects/52 tree nodes in both builds, with identical relative texture dependency sets: group0 IDs4144,4152,4664,5152 and group2 ID2048. Matching Parts/LOD slots rather than raw slot numbers maps February main-body3 to retail0, February0/1/2 to retail8/9/10, and alternate9 to6. Two mapped lower-detail payloads are byte-identical; other differences include tree metadata and an enlarged main-body packet. Equal dependency IDs are not proof of equal texture payloads or driving behavior. DIAMOND/PU_INNER5011 both have5 tree nodes and group0 texture2108, strengthening the changed-successor lead; their geometry streams still differ and have not been rendered for comparison.

Read-only February/retail comparison maps Object3D_ParseO3D16BFD0 ->169720 (identical bytes), Object3D_ParseData16C670 ->169E00 (identical normalized instruction structure), and OL_spParseObjectFromStream12FF80 ->12C860 (Ghidra bodies agree after mapped callees). ParseData walks sized Part/Gmd /Obf /ExpF chunks, resolves up to32 object slots, links parts, and calls the destination build's fragment-header initializer. ParseO3D relocates four main and four alternate object indices in place; the raw streamed resource is not already a runtime object. The lower-level parser allocates/rebuilds its tree and resolves textures through the active texture-group manager.

Fragment initialization is not identical: February16C420 unconditionally sets the alpha-blending bit in PRMODE (0x50 plus context selection); retail169BA0 uses0x10 plus the texture record's+45 flag shifted into bit6. Both use texture records of0x48 bytes and fragment stride0x7F0. A restoration should feed raw validated resources through retail's loaders so retail rebuilds these headers. Copying prototype-built rendering state would preserve the wrong behavior. Texture dependencies and tree/geometry formats still need validation before any live swap.

Python chunk audit verified each selected decoded payload against the existing independent SHA256 inventory; no files were extracted. Silver Streak/model20 COMPACT_A(10060) and_C(10062) already match all builds. COMPACT_B(10061) differs: February215920bytes, retail/March215952. Both contain12 Part,7 Gmd and11 Obf chunks; several main-body Obf blocks are reordered and one grows32bytes. This is an earlier version candidate, not an additional car. The actual tree/material/vertex differences remain to be decoded.

DIAMOND(5011) in February and PU_INNER(5011) in retail/March each contain a112-byte Gmd plus5408-byte Obf, totaling5520bytes. Their hashes and numeric payloads differ, but matching ID/size/chunk layout makes a changed/renamed successor a concrete possibility. Do not describe DIAMOND as a confirmed wholly removed object until geometry/material comparison resolves that relationship. The earlier name/hash inventory remains accurate but does not prove semantic absence.
