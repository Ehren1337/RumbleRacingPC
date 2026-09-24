"""Reproduce the supported Rumble Racing retail PC port from a user's own files.

Python 3.10+, Git, CMake and a C++20 toolchain. No game download or embedded Python.
The public tree is source/metadata only; local state and generated code are ignored.
"""
import argparse
import configparser
import math
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".port"
PROFILE = "RelWithDebInfo"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lock():
    lock = json.loads((ROOT / "port-lock.json").read_text(encoding="utf-8"))
    for name, expected in lock["files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Published recipe changed: {name}; review and update its lock deliberately")
    return lock


def command_environment(base=None):
    env = dict(os.environ if base is None else base)
    if os.name == "nt":
        env = {key.upper(): value for key, value in env.items()}
        # Diligent's nested shader fixtures exceed legacy Windows path limits.
        # Scope this to child Git processes, including CMake's submodule clones.
        count = int(env.get("GIT_CONFIG_COUNT", "0"))
        env[f"GIT_CONFIG_KEY_{count}"] = "core.longpaths"
        env[f"GIT_CONFIG_VALUE_{count}"] = "true"
        env["GIT_CONFIG_COUNT"] = str(count + 1)
    return env


def command(args, cwd=None, **kwargs):
    env = command_environment(kwargs.pop("env", None))
    return subprocess.run([str(x) for x in args], cwd=cwd, check=True, env=env, **kwargs)


def git(source, *args):
    return command(["git", "-C", source, *args], capture_output=True, text=True).stdout.strip()


def read_state():
    path = LOCAL / "state.json"
    if not path.exists():
        raise ValueError("Run port.py setup first")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def verify_source(source, lock):
    if git(source, "rev-parse", "HEAD") != lock["upstream_revision"]:
        raise ValueError("Engine revision differs from the locked upstream revision")
    # Verify every post-patch file, including new files. Generated runner files
    # are intentionally absent from the patch and are checked separately.
    patch = (ROOT / "patches/runtime.patch").read_text(encoding="utf-8")
    for section in patch.split("diff --git ")[1:]:
        name = section.splitlines()[0].split(" b/", 1)[1]
        match = re.search(r"^index [0-9a-f]+\.\.([0-9a-f]+)", section, re.M)
        if not match or git(source, "hash-object", "--path=" + name, name) != match[1]:
            raise ValueError(f"Engine source differs from the tested snapshot: {name}")


def setup(args, lock):
    source = (args.source or ROOT / ".engine/PS2Recomp").resolve()
    fresh = not source.exists()
    if fresh:
        source.parent.mkdir(parents=True, exist_ok=True)
        command(["git", "clone", lock["upstream_url"], source])
        command(["git", "-C", source, "checkout", "--detach", lock["upstream_revision"]])
    if git(source, "rev-parse", "HEAD") != lock["upstream_revision"]:
        raise ValueError("Existing source is at a different revision; no checkout/reset performed")
    patch = ROOT / "patches/runtime.patch"
    reverse = subprocess.run(["git", "-C", str(source), "apply", "--reverse", "--check", str(patch)],
                             capture_output=True)
    if reverse.returncode:
        if git(source, "status", "--porcelain"):
            raise ValueError("Existing source has local changes; refusing to patch over them")
        command(["git", "-C", source, "apply", "--check", patch])
        command(["git", "-C", source, "apply", patch])
    if fresh:
        command(["git", "-C", source, "submodule", "update", "--init", "--recursive"])
    verify_source(source, lock)
    state = {"source": str(source), "gpu": not args.cpu_renderer, "ffmpeg": not args.no_ffmpeg}
    previous = LOCAL / "state.json"
    if previous.exists():
        old = read_state()
        if old.get("source") == str(source) and "disc" in old:
            state["disc"] = old["disc"]
    write_json(previous, state)
    print("Source verified. Next: python port.py generate --disc <EXTRACTED_DISC_DIRECTORY>")


def configure(state):
    source = Path(state["source"])
    command(["cmake", "-S", source, "-B", source / "out/build",
             "-DCMAKE_BUILD_TYPE=" + PROFILE, "-DFETCHCONTENT_UPDATES_DISCONNECTED=ON",
             "-DPS2X_ENABLE_RUNTIME_LOGS=ON",
             "-DPS2X_ENABLE_DILIGENT_GS=" + ("ON" if state["gpu"] else "OFF"),
             "-DPS2X_ENABLE_FFMPEG=" + ("ON" if state["ffmpeg"] else "OFF")])


def build_target(source, target):
    env = dict(os.environ)
    if os.name == "nt":
        # Avoid duplicate Path/PATH environment entries in Windows MSBuild.
        env = {key.upper(): value for key, value in env.items()}
        env["MSBUILDDISABLENODEREUSE"] = "1"
        env["CL"] = env.get("CL", "") + " /MP4"
    command(["cmake", "--build", source / "out/build", "--config", PROFILE,
             "--target", target, "--parallel", "4"], env=env)


def executable(source, component, name):
    suffix = ".exe" if os.name == "nt" else ""
    base = source / "out/build" / component
    for path in [base / PROFILE / (name + suffix), base / (name + suffix)]:
        if path.is_file():
            return path
    raise ValueError(f"Missing {name}; build it first")


def verify_disc(disc, lock):
    disc = disc.resolve()
    required = {lock["elf"]: lock["elf_sha256"], "MODULES/AUDIO.IRX": lock["audio_module_sha256"]}
    for name, expected in required.items():
        if not (disc / name).is_file() or sha(disc / name) != expected:
            raise ValueError(f"Wrong or missing retail file: {name}")
    if not (disc / "DATA").is_dir() or not (disc / "GLBLDATA.PS2").is_file():
        raise ValueError("Supply the complete extracted disc beside its ELF, not only the ELF")
    return disc


def generated_digest(files):
    result = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.name):
        result.update(path.name.encode() + b"\0")
        result.update(hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).digest())
    return result.hexdigest()


def runtime_target(source, name):
    if Path(name).name != name or Path(name).suffix not in (".h", ".cpp"):
        raise ValueError("Invalid generated filename")
    runtime = (source / "ps2xRuntime").resolve()
    target = (runtime / ("include" if name.endswith(".h") else "src/runner") / name).resolve()
    if not target.is_relative_to(runtime):
        raise ValueError("Generated target escaped runtime directory")
    return target


def stage_generated(source, files, previous):
    # Validate the entire update before writing/removing any source file.
    next_hashes = {p.name: sha(p) for p in files}
    writes, removes = [], []
    for path in files:
        target = runtime_target(source, path.name)
        if target.exists() and sha(target) != next_hashes[path.name]:
            allowed = previous.get(path.name) == sha(target)
            if not allowed and path.name == "register_functions.cpp":
                original = command(["git", "-C", source, "show", "HEAD:ps2xRuntime/src/runner/register_functions.cpp"],
                                   capture_output=True).stdout
                allowed = target.read_bytes().replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n")
            if not allowed:
                raise ValueError(f"Preserving independently edited generated file: {target}")
        if not target.exists() or sha(target) != next_hashes[path.name]:
            writes.append((path, target))
    for name, expected in previous.items():
        if name not in next_hashes:
            target = runtime_target(source, name)
            if target.exists():
                if sha(target) != expected:
                    raise ValueError(f"Preserving independently edited obsolete file: {target}")
                removes.append(target)
    for path, target in writes:
        target.write_bytes(path.read_bytes())
    for target in removes:
        target.unlink()
    return next_hashes, len(writes), len(removes)


def generate(args, state, lock):
    source = Path(state["source"])
    verify_source(source, lock)
    disc = verify_disc(args.disc, lock)
    if args.recompiler:
        compiler = args.recompiler.resolve()
    else:
        configure(state)
        build_target(source, "ps2_recomp")
        compiler = executable(source, "ps2xRecomp", "ps2_recomp")
    LOCAL.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="generate-", dir=LOCAL) as temp:
        folder = Path(temp).resolve()
        if not folder.is_relative_to(LOCAL.resolve()):
            raise ValueError("Temporary output escaped local state directory")
        output = folder / "output"
        output.mkdir()
        text = (ROOT / "config/retail.toml").read_text(encoding="utf-8")
        for marker, path in {"@ELF@": disc / lock["elf"], "@OUTPUT@": output,
                             "@MAP@": ROOT / "config/retail-functions.csv"}.items():
            text = text.replace('"' + marker + '"', json.dumps(path.as_posix()))
        config = folder / "generate.toml"
        config.write_text(text, encoding="utf-8")
        with (LOCAL / "generate.log").open("w", encoding="utf-8") as log:
            command([compiler, config], stdout=log, stderr=subprocess.STDOUT)
        files = list(output.glob("*.cpp")) + list(output.glob("*.h"))
        if len(files) != lock["generated_files"] or generated_digest(files) != lock["generated_tree_sha256"]:
            raise ValueError("Generated source differs from the tested port; nothing staged. See .port/generate.log")
        if args.check:
            print(f"Verified {len(files)} generated files against the working port; source unchanged")
            return
        manifest = LOCAL / "generated.json"
        previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
        hashes, writes, removes = stage_generated(source, files, previous)
        write_json(manifest, hashes)
        state["disc"] = str(disc)
        write_json(LOCAL / "state.json", state)
        print(f"Verified {len(files)} generated files; wrote {writes}, removed {removes}. Next: python port.py build")


def check_staged(source, lock):
    manifest = LOCAL / "generated.json"
    if not manifest.exists():
        raise ValueError("Run port.py generate first")
    names = json.loads(manifest.read_text(encoding="utf-8"))
    files = [runtime_target(source, name) for name in names]
    if len(files) != lock["generated_files"] or generated_digest(files) != lock["generated_tree_sha256"]:
        raise ValueError("Staged game code differs from the tested port; review edits before building/running")


def keyboard_bindings(profile):
    """Import only Pad1 keyboard bindings; never modify the PCSX2 profile."""
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    with Path(profile).open(encoding="utf-8-sig") as source:
        config.read_file(source)
    if not config.has_section("Pad1") or config["Pad1"].get("Type") != "DualShock2":
        raise ValueError("Expected a PCSX2 DualShock2 Pad1 profile")
    names = ("Select", "L3", "R3", "Start", "Up", "Right", "Down", "Left",
             "L2", "R2", "L1", "R1", "Triangle", "Circle", "Cross", "Square",
             "LLeft", "LRight", "LUp", "LDown", "RLeft", "RRight", "RUp", "RDown")
    keys = {chr(n): str(n) for n in range(ord('A'), ord('Z') + 1)}
    keys.update({str(n): str(48 + n) for n in range(10)})
    keys.update({f"Numpad{n}": str(320 + n) for n in range(10)})
    keys.update({"Up": "265", "Down": "264", "Left": "263", "Right": "262",
                 "Return": "257", "Tab": "258", "Space": "32", "Escape": "256",
                 "Alt": "342,346", "Control": "341,345", "Shift": "340,344"})
    bindings = []
    for name in names:
        source = config["Pad1"].get(name, "")
        if not source:
            continue
        if source.startswith("SDL-") and "Keyboard/" not in source:
            continue  # Physical gamepad input remains handled by the runtime.
        if not source.startswith("Keyboard/") or source[9:] not in keys:
            raise ValueError(f"Unsupported profile binding for {name}: {source}")
        bindings.append(f"{name}={keys[source[9:]]}")
    if not bindings:
        raise ValueError("This profile contains no supported keyboard bindings")
    return ";".join(bindings)


def benchmark_pose(record, expected_hash):
    """Validate a saved retail pose before passing it to the native dev hook."""
    if record.get("schema_version") != 1 or record.get("elf_sha256") != expected_hash:
        raise ValueError("Benchmark spot belongs to an unverified game build")
    track = record["track_id"]
    if type(track) is not int or not 0 <= track < 15:
        raise ValueError("Invalid benchmark track")
    matrix = record.get("matrix", record.get("research_pose", {}).get("car_matrix_f32"))
    if not isinstance(matrix, list) or len(matrix) != 16 or not all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in matrix):
        raise ValueError("Benchmark spot needs a finite 4x4 car pose")
    if any(matrix[i] != 0 for i in (3, 7, 11)) or matrix[15] != 1:
        raise ValueError("Invalid affine pose")
    axes = [matrix[i:i + 3] for i in (0, 4, 8)]
    dot = lambda a, b: sum(x*y for x, y in zip(a, b))
    if any(abs(dot(a, a)-1) > .02 for a in axes) or any(
            abs(dot(axes[a], axes[b])) > .02 for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Pose orientation is not orthonormal")
    a, b, c = axes
    determinant = sum(a[i]*(b[(i+1)%3]*c[(i+2)%3]-b[(i+2)%3]*c[(i+1)%3]) for i in range(3))
    if determinant < .98 or any(abs(v) > 100000 for v in matrix[12:15]):
        raise ValueError("Reflected pose or position outside development bounds")
    if record["position"] != matrix[12:15]:
        raise ValueError("Saved coordinates disagree with the pose")
    return str(track) + " " + " ".join(format(v, ".9g") for v in matrix)


def process_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    # os.kill(pid, 0) is NOT a harmless probe on Windows. Query only.
    import ctypes as c
    api = c.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [c.c_uint, c.c_int, c.c_uint]
    api.OpenProcess.restype = c.c_void_p
    api.GetExitCodeProcess.argtypes = [c.c_void_p, c.POINTER(c.c_uint)]
    api.CloseHandle.argtypes = [c.c_void_p]
    handle = api.OpenProcess(0x1000, False, pid)
    if not handle:
        return c.get_last_error() == 5  # Access denied: do not assume stopped.
    try:
        status = c.c_uint()
        return not api.GetExitCodeProcess(handle, c.byref(status)) or status.value == 259
    finally:
        api.CloseHandle(handle)


def run(args, state, lock):
    source = Path(state["source"])
    verify_source(source, lock)
    check_staged(source, lock)
    disc = verify_disc(Path(state["disc"]), lock)
    runner = executable(source, "ps2xRuntime", "ps2EntryRunner")
    # Do not launch a stale executable after regeneration or source edits.
    newest = max(p.stat().st_mtime for p in [runtime_target(source, name)
                 for name in json.loads((LOCAL / "generated.json").read_text())])
    if runner.stat().st_mtime < newest:
        raise ValueError("Runner predates generated source; run port.py build")
    if (args.car is None) != (args.track is None):
        raise ValueError("Direct race requires both --car and --track")
    if args.car is not None and not (0 <= args.car < 36 and 0 <= args.track < 15):
        raise ValueError("Retail car/track ID outside supported range")
    report = source / "out/build/ps2xRuntime/inspector.json"
    if report.exists():
        try:
            old = json.loads(report.read_text(encoding="utf-8-sig"))
            alive = process_alive(int(old["process_id"]))
        except (OSError, ValueError, KeyError):
            pass
        else:
            if alive:
                raise ValueError("The previous runner PID is still alive; close it before another launch")
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("PS2_RUMBLE_DEV_"):
            env.pop(key)
    env.update(PS2_GS_THREADED="1", PS2_GS_GPU_PRESENT="1", PS2_GS_GPU_ASYNC_PRESENT="1",
               PS2_GS_ASYNC_TEXFLUSH="1", PS2_GS_ASYNC_LOCAL_COPY="1", PS2_GS_DEPTH_PREFETCH="1",
               PS2_GS_GPU_PROFILE="0", PS2_RUMBLE_NATIVE_VU="1", PS2_RUMBLE_VU_COMPARE="1",
               PS2_WINDOW_HIDDEN="0", PS2_WINDOW_WIDTH="1280", PS2_WINDOW_HEIGHT="720",
               PS2_DISPLAY_ASPECT="4:3", PS2_INSPECTOR_FILE=str(report), PS2_INSPECTOR_FRAME="0",
               PS2_INSPECTOR_WATCHES="race_phase=0x1f21e4:4;race_clock=0x1f22b8:4")
    for name in ("CLIP", "REFLECT", "LIT", "REFLECT_LIT", "DUAL_BASIS", "QUAD"):
        env["PS2_RUMBLE_NATIVE_VU_" + name] = "1"
    if state["gpu"]:
        env["PS2_GS_GPU"] = args.gpu or ("d3d11" if os.name == "nt" else "vulkan")
    else:
        env.pop("PS2_GS_GPU", None)
    if args.car is not None:
        env["PS2_RUMBLE_DEV_RACE"] = f"{args.car} {args.track} 0"
    if args.keyboard_profile:
        env["PS2_PAD_KEYS"] = keyboard_bindings(args.keyboard_profile)
    if args.spot:
        pose = json.loads(args.spot.read_text(encoding="utf-8"))
        setting = benchmark_pose(pose, lock["elf_sha256"])
        if args.track is not None and pose["track_id"] != args.track:
            raise ValueError("Saved pose belongs to a different track")
        env["PS2_RUMBLE_DEV_TELEPORT"] = setting
    if args.ai:
        env["PS2_RUMBLE_DEV_AI"] = "no-mercy"
    if args.max_upgrades:
        env["PS2_RUMBLE_DEV_UPGRADES"] = "player-elite"
    with (report.parent / "ntsc-runner-stdout.log").open("w") as stdout, (report.parent / "ntsc-runner-stderr.log").open("w") as stderr:
        process = subprocess.Popen([str(runner), str(disc / lock["elf"])], cwd=runner.parent,
                                   env=env, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    print(f"Started PID {process.pid}; manual controls unless --ai. Inspector: {report}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare = commands.add_parser("setup", help="Fetch/apply locked source, or adopt a matching existing checkout")
    prepare.add_argument("--source", type=Path)
    prepare.add_argument("--cpu-renderer", action="store_true")
    prepare.add_argument("--no-ffmpeg", action="store_true")
    gen = commands.add_parser("generate", help="Verify disc and reproduce/stage the known game source")
    gen.add_argument("--disc", type=Path, required=True)
    gen.add_argument("--recompiler", type=Path, help="Use an already built recompiler; skip configure/build")
    gen.add_argument("--check", action="store_true", help="Verify reproduction only; do not stage game source")
    commands.add_parser("build", help="Build the prepared native runner in the existing build directory")
    start = commands.add_parser("run", help="Launch the matching runner with optional retail development settings")
    start.add_argument("--car", type=int, help="Retail driver ID; e.g. 6 = Tiberius")
    start.add_argument("--track", type=int, help="Retail track ID; e.g. 10 = True Grits")
    start.add_argument("--gpu", choices=("d3d11", "d3d12", "vulkan"))
    start.add_argument("--keyboard-profile", type=Path, help="Read a PCSX2 Pad1 keyboard profile")
    start.add_argument("--spot", type=Path, help="Private saved pose JSON; teleport three game seconds after GO")
    start.add_argument("--ai", action="store_true")
    start.add_argument("--max-upgrades", action="store_true")
    args = parser.parse_args()
    lock = load_lock()
    if args.action == "setup":
        setup(args, lock)
        return
    state = read_state()
    if args.action == "generate":
        generate(args, state, lock)
    elif args.action == "build":
        source = Path(state["source"])
        verify_source(source, lock)
        check_staged(source, lock)
        configure(state)
        build_target(source, "ps2EntryRunner")
    else:
        run(args, state, lock)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"RumbleRacingPC: {error}", file=sys.stderr)
        sys.exit(1)
