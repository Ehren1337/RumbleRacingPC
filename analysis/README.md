# Research notes

Reviewed written findings and compact analysis metadata from the Rumble Racing port investigation. These help continue the research; they are not a complete archive of the original analysis workspace.

| File | Contents |
| --- | --- |
| [Porting summary](PORTING-SUMMARY.md) | Current reproducible baseline, major changes and unresolved work. |
| [Simulation handoff](../RUMBLE-RACING-SIMULATION-HANDOFF.md) | Detailed execution/rendering architecture, measurements, correctness requirements and next investigations. |
| [Assets and debug findings](ASSETS-AND-DEBUG.md) | Historical prototype/retail comparisons, debug-console interfaces, vehicle/object candidates and important uncertainty. |
| [Function matches](retail-exact-function-matches.csv) | 177 individually identified February-to-retail function matches: names, addresses, byte lengths and comparison method. No function bodies. |
| [Disc-file comparison](prototype-vs-retail-files.csv) | 72 February-versus-retail file rows: paths relative to the discs, sizes, SHA-256 hashes and comparison status. No file payloads. |
| [Debug command counts](debug-command-strings.csv) | Occurrence counts for 15 command names. A matching string does not prove a working command. |

The function-match CSV is a limited research result, not a complete prototype symbol database or proof that debug features were ported. Build boundaries/bindings are separately locked in `../config/`. The asset notes are dated research snapshots; later implementation status is in the porting summary and project README. Addresses apply only to the identified builds.

## What remains local

The raw Ghidra project, prototype linker map, generated/decompiled code, full chronological `PORTING-STATUS.md`, raw JSON inventories/memory samples, ETL captures, screenshots, video and game assets are **not included**. Some notes reference these original evidence files; those references do not mean the files are distributed here. Their absence limits independent reproduction of the historical measurements; repeat the analysis on your own matching inputs when checking a claim.

The separately published [workflow toolkit](https://github.com/Ehren1337/PS2RecompAIWorkflow/tree/74c849130cda63af33095d50088152465139d266/Rumble%20Racing) contains research/navigation scripts and Ghidra helpers. They are not automatically installed by this repository and need their documented workspace layout. Normal port generation/building uses `port.py` and does not require those tools or private Ghidra data.

This publication preserves the reviewed findings, not every abandoned experiment or live-state snapshot. Retain the original local research if you need to resume from its exact analysis state. No build, asset or saved-game file was moved into this folder for publication.
